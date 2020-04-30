package quic

import (
	"errors"
	"fmt"
	"math/rand"
	"sort"
	"sync"
	"time"

	"github.com/lucas-clemente/quic-go/internal/handshake"
	"github.com/lucas-clemente/quic-go/internal/protocol"
	"github.com/lucas-clemente/quic-go/internal/utils"
	"github.com/lucas-clemente/quic-go/qerr"
)

type streamsMap struct {
	mutex sync.RWMutex

	perspective          protocol.Perspective
	connectionParameters handshake.ConnectionParametersManager

	streams map[protocol.StreamID]*stream

	// needed for round-robin scheduling
	openStreams           []protocol.StreamID
	roundRobinIndex       uint32 // used by RoundRobinIterate()
	roundRobinIndexSend   uint32 // avoid collision, used by RoundRobinIterateSend()
	roundRobinIndexStream uint32 // used by RoundRobinIteratePopOfPath()

	nextStream                protocol.StreamID // StreamID of the next Stream that will be returned by OpenStream()
	highestStreamOpenedByPeer protocol.StreamID
	nextStreamOrErrCond       sync.Cond
	openStreamOrErrCond       sync.Cond

	closeErr           error
	nextStreamToAccept protocol.StreamID

	newStream             newStreamLambda
	newStreamPriority     newStreamLambdaPriority
	newStreamPrioritySize newStreamLambdaPrioritySize
	priorityOrder         []protocol.StreamID //stream id list sorted by priority for each time of path scheduling

	numOutgoingStreams uint32
	numIncomingStreams uint32

	streamTree *streamTree
}

type streamLambda func(*stream) (bool, error)
type streamLambdaSend func(*stream) (bool, bool, bool, error)
type newStreamLambda func(protocol.StreamID) *stream

type newStreamLambdaPriority func(protocol.StreamID, *protocol.Priority) *stream
type newStreamLambdaPrioritySize func(protocol.StreamID, *protocol.Priority) *stream

var (
	errMapAccess = errors.New("streamsMap: Error accessing the streams map")
)

func newStreamsMap(newStream newStreamLambda, pers protocol.Perspective, connectionParameters handshake.ConnectionParametersManager) *streamsMap {
	sm := streamsMap{
		perspective:          pers,
		streams:              map[protocol.StreamID]*stream{},
		openStreams:          make([]protocol.StreamID, 0),
		newStream:            newStream,
		connectionParameters: connectionParameters,
		priorityOrder:        make([]protocol.StreamID, 0),
	}
	sm.nextStreamOrErrCond.L = &sm.mutex
	sm.openStreamOrErrCond.L = &sm.mutex

	if pers == protocol.PerspectiveClient {
		sm.nextStream = 1
		sm.nextStreamToAccept = 2
	} else {
		sm.nextStream = 2
		sm.nextStreamToAccept = 1
	}

	return &sm
}

func newStreamsMapPriority(newStreamPriority newStreamLambdaPriority, pers protocol.Perspective, connectionParameters handshake.ConnectionParametersManager) *streamsMap {
	sm := streamsMap{
		perspective:          pers,
		streams:              map[protocol.StreamID]*stream{},
		openStreams:          make([]protocol.StreamID, 0),
		newStreamPriority:    newStreamPriority,
		connectionParameters: connectionParameters,
		priorityOrder:        make([]protocol.StreamID, 0),
	}
	sm.nextStreamOrErrCond.L = &sm.mutex
	sm.openStreamOrErrCond.L = &sm.mutex

	if pers == protocol.PerspectiveClient {
		sm.nextStream = 1
		sm.nextStreamToAccept = 2
	} else {
		sm.nextStream = 2
		sm.nextStreamToAccept = 1
	}

	return &sm
}

func newStreamsMapPrioritySize(newStreamPrioritySize newStreamLambdaPrioritySize, pers protocol.Perspective, connectionParameters handshake.ConnectionParametersManager) *streamsMap {
	sm := streamsMap{
		perspective:           pers,
		streams:               map[protocol.StreamID]*stream{},
		openStreams:           make([]protocol.StreamID, 0),
		newStreamPrioritySize: newStreamPrioritySize,
		connectionParameters:  connectionParameters,
		priorityOrder:         make([]protocol.StreamID, 0),
	}
	sm.nextStreamOrErrCond.L = &sm.mutex
	sm.openStreamOrErrCond.L = &sm.mutex

	if pers == protocol.PerspectiveClient {
		sm.nextStream = 1
		sm.nextStreamToAccept = 2
	} else {
		sm.nextStream = 2
		sm.nextStreamToAccept = 1
	}

	return &sm
}

func newStreamsMapTree(newStreamPrioritySize newStreamLambdaPrioritySize,
	pers protocol.Perspective,
	connectionParameters handshake.ConnectionParametersManager,
	streamTree *streamTree) *streamsMap {
	sm := streamsMap{
		perspective:           pers,
		streams:               map[protocol.StreamID]*stream{},
		openStreams:           make([]protocol.StreamID, 0),
		newStreamPrioritySize: newStreamPrioritySize,
		connectionParameters:  connectionParameters,
		streamTree:            streamTree,
	}
	sm.nextStreamOrErrCond.L = &sm.mutex
	sm.openStreamOrErrCond.L = &sm.mutex

	if pers == protocol.PerspectiveClient {
		sm.nextStream = 1
		sm.nextStreamToAccept = 2
	} else {
		sm.nextStream = 2
		sm.nextStreamToAccept = 1
	}

	return &sm
}

// GetOrOpenStream either returns an existing stream, a newly opened stream, or nil if a stream with the provided ID is already closed.
// Newly opened streams should only originate from the client. To open a stream from the server, OpenStream should be used.
func (m *streamsMap) GetOrOpenStream(id protocol.StreamID) (*stream, error) {
	m.mutex.RLock()
	s, ok := m.streams[id]
	m.mutex.RUnlock()
	if ok {
		return s, nil // s may be nil
	}

	// ... we don't have an existing stream
	m.mutex.Lock()
	defer m.mutex.Unlock()
	// We need to check whether another invocation has already created a stream (between RUnlock() and Lock()).
	s, ok = m.streams[id]
	if ok {
		return s, nil
	}

	if m.perspective == protocol.PerspectiveServer {
		if id%2 == 0 {
			if id <= m.nextStream { // this is a server-side stream that we already opened. Must have been closed already
				return nil, nil
			}
			return nil, qerr.Error(qerr.InvalidStreamID, fmt.Sprintf("attempted to open stream %d from client-side", id))
		}
		if id <= m.highestStreamOpenedByPeer { // this is a client-side stream that doesn't exist anymore. Must have been closed already
			return nil, nil
		}
	}
	if m.perspective == protocol.PerspectiveClient {
		if id%2 == 1 {
			if id <= m.nextStream { // this is a client-side stream that we already opened.
				return nil, nil
			}
			return nil, qerr.Error(qerr.InvalidStreamID, fmt.Sprintf("attempted to open stream %d from server-side", id))
		}
		if id <= m.highestStreamOpenedByPeer { // this is a server-side stream that doesn't exist anymore. Must have been closed already
			return nil, nil
		}
	}

	// sid is the next stream that will be opened
	sid := m.highestStreamOpenedByPeer + 2
	// if there is no stream opened yet, and this is the server, stream 1 should be openend
	if sid == 2 && m.perspective == protocol.PerspectiveServer {
		sid = 1
	}

	for ; sid <= id; sid += 2 {
		_, err := m.openRemoteStream(sid)
		if err != nil {
			return nil, err
		}
		if utils.Debug() {
			utils.Debugf("SHI: Get or open stream %d on perspective %x\n", sid, m.perspective)
		}
	}

	m.nextStreamOrErrCond.Broadcast()

	//SHI: add log
	m.streamTree.printTree()

	return m.streams[id], nil
}

func (m *streamsMap) GetOrOpenStreamPriority(id protocol.StreamID, priority *protocol.Priority) (*stream, error) {
	m.mutex.RLock()
	s, ok := m.streams[id]
	m.mutex.RUnlock()
	if ok {
		return s, nil // s may be nil
	}

	// ... we don't have an existing stream
	m.mutex.Lock()
	defer m.mutex.Unlock()
	// We need to check whether another invocation has already created a stream (between RUnlock() and Lock()).
	s, ok = m.streams[id]
	if ok {
		return s, nil
	}

	if m.perspective == protocol.PerspectiveServer {
		if id%2 == 0 {
			if id <= m.nextStream { // this is a server-side stream that we already opened. Must have been closed already
				return nil, nil
			}
			return nil, qerr.Error(qerr.InvalidStreamID, fmt.Sprintf("attempted to open stream %d from client-side", id))
		}
		if id <= m.highestStreamOpenedByPeer { // this is a client-side stream that doesn't exist anymore. Must have been closed already
			return nil, nil
		}
	}
	if m.perspective == protocol.PerspectiveClient {
		if id%2 == 1 {
			if id <= m.nextStream { // this is a client-side stream that we already opened.
				return nil, nil
			}
			return nil, qerr.Error(qerr.InvalidStreamID, fmt.Sprintf("attempted to open stream %d from server-side", id))
		}
		if id <= m.highestStreamOpenedByPeer { // this is a server-side stream that doesn't exist anymore. Must have been closed already
			return nil, nil
		}
	}

	// sid is the next stream that will be opened
	sid := m.highestStreamOpenedByPeer + 2
	// if there is no stream opened yet, and this is the server, stream 1 should be openend
	if sid == 2 && m.perspective == protocol.PerspectiveServer {
		sid = 1
	}

	for ; sid <= id; sid += 2 {
		_, err := m.openRemoteStreamPriority(sid, priority)
		if err != nil {
			return nil, err
		}
		if utils.Debug() {
			utils.Debugf("SHI: GetOrOpenStreamPriority: Get or open stream %d with priority %d on perspective %x\n", sid, priority, m.perspective)
		}
	}

	m.nextStreamOrErrCond.Broadcast()
	return m.streams[id], nil
}

func (m *streamsMap) GetOrOpenStreamPrioritySize(id protocol.StreamID, priority *protocol.Priority) (*stream, error) {
	m.mutex.RLock()
	s, ok := m.streams[id]
	m.mutex.RUnlock()
	if ok {
		return s, nil // s may be nil
	}

	// ... we don't have an existing stream
	m.mutex.Lock()
	defer m.mutex.Unlock()
	// We need to check whether another invocation has already created a stream (between RUnlock() and Lock()).
	s, ok = m.streams[id]
	if ok {
		return s, nil
	}

	if m.perspective == protocol.PerspectiveServer {
		if id%2 == 0 {
			if id <= m.nextStream { // this is a server-side stream that we already opened. Must have been closed already
				return nil, nil
			}
			return nil, qerr.Error(qerr.InvalidStreamID, fmt.Sprintf("attempted to open stream %d from client-side", id))
		}
		if id <= m.highestStreamOpenedByPeer { // this is a client-side stream that doesn't exist anymore. Must have been closed already
			return nil, nil
		}
	}
	if m.perspective == protocol.PerspectiveClient {
		if id%2 == 1 {
			if id <= m.nextStream { // this is a client-side stream that we already opened.
				return nil, nil
			}
			return nil, qerr.Error(qerr.InvalidStreamID, fmt.Sprintf("attempted to open stream %d from server-side", id))
		}
		if id <= m.highestStreamOpenedByPeer { // this is a server-side stream that doesn't exist anymore. Must have been closed already
			return nil, nil
		}
	}

	// sid is the next stream that will be opened
	sid := m.highestStreamOpenedByPeer + 2
	// if there is no stream opened yet, and this is the server, stream 1 should be openend
	if sid == 2 && m.perspective == protocol.PerspectiveServer {
		sid = 1
	}

	for ; sid <= id; sid += 2 {
		_, err := m.openRemoteStreamPrioritySize(sid, priority)
		if err != nil {
			return nil, err
		}
		if utils.Debug() {
			utils.Debugf("SHI: GetOrOpenStreamPrioritySize: Get or open stream %d with priority %d, size %d on perspective %x\n", sid, priority.Weight, m.perspective)
		}
	}

	m.nextStreamOrErrCond.Broadcast()

	return m.streams[id], nil
}

func (m *streamsMap) openRemoteStream(id protocol.StreamID) (*stream, error) {
	if m.numIncomingStreams >= m.connectionParameters.GetMaxIncomingStreams() {
		return nil, qerr.TooManyOpenStreams
	}
	if id+protocol.MaxNewStreamIDDelta < m.highestStreamOpenedByPeer {
		return nil, qerr.Error(qerr.InvalidStreamID, fmt.Sprintf("attempted to open stream %d, which is a lot smaller than the highest opened stream, %d", id, m.highestStreamOpenedByPeer))
	}

	if m.perspective == protocol.PerspectiveServer {
		m.numIncomingStreams++
	} else {
		m.numOutgoingStreams++
	}

	if id > m.highestStreamOpenedByPeer {
		m.highestStreamOpenedByPeer = id
	}

	priority := &protocol.Priority{Weight: ^uint8(0), Dependency: 0, Exclusive: false}
	//fmt.Printf("\nstreamsMap.openRemoteStream(): weight %d\n", priority.Weight)

	s := m.newStreamPrioritySize(id, priority)
	m.putStream(s)
	return s, nil
}

func (m *streamsMap) openRemoteStreamPriority(id protocol.StreamID, priority *protocol.Priority) (*stream, error) {
	if m.numIncomingStreams >= m.connectionParameters.GetMaxIncomingStreams() {
		return nil, qerr.TooManyOpenStreams
	}
	if id+protocol.MaxNewStreamIDDelta < m.highestStreamOpenedByPeer {
		return nil, qerr.Error(qerr.InvalidStreamID, fmt.Sprintf("attempted to open stream %d, which is a lot smaller than the highest opened stream, %d", id, m.highestStreamOpenedByPeer))
	}

	if m.perspective == protocol.PerspectiveServer {
		m.numIncomingStreams++
	} else {
		m.numOutgoingStreams++
	}

	if id > m.highestStreamOpenedByPeer {
		m.highestStreamOpenedByPeer = id
	}

	s := m.newStreamPrioritySize(id, priority)
	m.putStream(s)
	return s, nil
}

func (m *streamsMap) openRemoteStreamPrioritySize(id protocol.StreamID, priority *protocol.Priority) (*stream, error) {
	if m.numIncomingStreams >= m.connectionParameters.GetMaxIncomingStreams() {
		return nil, qerr.TooManyOpenStreams
	}
	if id+protocol.MaxNewStreamIDDelta < m.highestStreamOpenedByPeer {
		return nil, qerr.Error(qerr.InvalidStreamID, fmt.Sprintf("attempted to open stream %d, which is a lot smaller than the highest opened stream, %d", id, m.highestStreamOpenedByPeer))
	}

	if m.perspective == protocol.PerspectiveServer {
		m.numIncomingStreams++
	} else {
		m.numOutgoingStreams++
	}

	if id > m.highestStreamOpenedByPeer {
		m.highestStreamOpenedByPeer = id
	}

	s := m.newStreamPrioritySize(id, priority)
	m.putStream(s)
	return s, nil
}

func (m *streamsMap) openStreamImpl() (*stream, error) {
	id := m.nextStream
	if m.numOutgoingStreams >= m.connectionParameters.GetMaxOutgoingStreams() {
		return nil, qerr.TooManyOpenStreams
	}

	if m.perspective == protocol.PerspectiveServer {
		m.numOutgoingStreams++
	} else {
		m.numIncomingStreams++
	}

	m.nextStream += 2

	priority := &protocol.Priority{Weight: ^uint8(0), Dependency: 0, Exclusive: false}
	s := m.newStreamPrioritySize(id, priority)
	m.putStream(s)
	return s, nil
}

func (m *streamsMap) openStreamPriorityImpl(priority *protocol.Priority) (*stream, error) {
	id := m.nextStream
	if m.numOutgoingStreams >= m.connectionParameters.GetMaxOutgoingStreams() {
		return nil, qerr.TooManyOpenStreams
	}

	if m.perspective == protocol.PerspectiveServer {
		m.numOutgoingStreams++
	} else {
		m.numIncomingStreams++
	}

	m.nextStream += 2
	s := m.newStreamPrioritySize(id, priority)
	m.putStream(s)

	//set priority of stream
	if m.streamTree != nil {
		err := m.streamTree.maybeSetWeight(id, priority.Weight)
		if err != nil {
			return nil, err
		}
		err = m.streamTree.maybeSetParent(id, priority.Dependency, priority.Exclusive)
		if err != nil {
			return nil, err
		}

	}

	if utils.Debug() {
		utils.Debugf("SHI: openStreamPriorityImpl(called by OpenStreamPrioritySync): stream %d, priority %d, perspective %x\n", s.streamID, s.priority, m.perspective)
	}
	return s, nil
}

func (m *streamsMap) openStreamPrioritySizeImpl(priority *protocol.Priority) (*stream, error) {
	id := m.nextStream
	if m.numOutgoingStreams >= m.connectionParameters.GetMaxOutgoingStreams() {
		return nil, qerr.TooManyOpenStreams
	}

	if m.perspective == protocol.PerspectiveServer {
		m.numOutgoingStreams++
	} else {
		m.numIncomingStreams++
	}

	m.nextStream += 2
	s := m.newStreamPrioritySize(id, priority)
	m.putStream(s)

	//set priority of stream
	if m.streamTree != nil {
		err := m.streamTree.maybeSetWeight(id, priority.Weight)
		if err != nil {
			return nil, err
		}
		err = m.streamTree.maybeSetParent(id, priority.Dependency, priority.Exclusive)
		if err != nil {
			return nil, err
		}

	}

	if utils.Debug() {
		utils.Debugf("SHI: openStreamPrioritySizeImpl(called by OpenStreamPrioritySizeSync): stream %d, priority %d, size%d, perspective %x\n", s.streamID, s.priority.Weight, m.perspective)
	}

	//SHI: add log
	m.streamTree.printTree()
	return s, nil
}

// OpenStream opens the next available stream
func (m *streamsMap) OpenStream() (*stream, error) {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	if m.closeErr != nil {
		return nil, m.closeErr
	}
	return m.openStreamImpl()
}

func (m *streamsMap) OpenStreamSync() (*stream, error) {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	for {
		if m.closeErr != nil {
			return nil, m.closeErr
		}
		str, err := m.openStreamImpl()
		if err == nil {
			return str, err
		}
		if err != nil && err != qerr.TooManyOpenStreams {
			return nil, err
		}
		m.openStreamOrErrCond.Wait()
	}
}

func (m *streamsMap) OpenStreamPrioritySync(priority *protocol.Priority) (*stream, error) {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	for {
		if m.closeErr != nil {
			return nil, m.closeErr
		}
		str, err := m.openStreamPriorityImpl(priority)
		if err == nil {
			return str, err
		}
		if err != nil && err != qerr.TooManyOpenStreams {
			return nil, err
		}
		m.openStreamOrErrCond.Wait()
	}
}

func (m *streamsMap) OpenStreamPrioritySizeSync(priority *protocol.Priority) (*stream, error) {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	for {
		if m.closeErr != nil {
			return nil, m.closeErr
		}
		str, err := m.openStreamPrioritySizeImpl(priority)
		if err == nil {
			return str, err
		}
		if err != nil && err != qerr.TooManyOpenStreams {
			return nil, err
		}
		m.openStreamOrErrCond.Wait()
	}
}

// AcceptStream returns the next stream opened by the peer
// it blocks until a new stream is opened
func (m *streamsMap) AcceptStream() (*stream, error) {
	m.mutex.Lock()
	defer m.mutex.Unlock()
	var str *stream
	for {
		var ok bool
		if m.closeErr != nil {
			return nil, m.closeErr
		}
		str, ok = m.streams[m.nextStreamToAccept]
		if ok {
			break
		}
		m.nextStreamOrErrCond.Wait()
	}
	m.nextStreamToAccept += 2
	return str, nil
}

func (m *streamsMap) Iterate(fn streamLambda) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	openStreams := append([]protocol.StreamID{}, m.openStreams...)

	for _, streamID := range openStreams {
		cont, err := m.iterateFunc(streamID, fn)
		if err != nil {
			return err
		}
		if !cont {
			break
		}
	}
	return nil
}

// RoundRobinIterate executes the streamLambda for every open stream, until the streamLambda returns false
// It uses a round-robin-like scheduling to ensure that every stream is considered fairly
// do not need round-robin index, because it does not permit interrupt or any failure when scheduling a stream to path
// It prioritizes the crypto- and the header-stream (StreamIDs 1 and 3)
func (m *streamsMap) RoundRobinIterateSchedule(fn streamLambda) (bool, error) {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	for _, id := range m.priorityOrder {
		cont, err := m.iterateFunc(id, fn)
		if err != nil {
			return false, err
		}
		if !cont {
			return false, nil
		}
	}

	return true, nil
}

//SHI: perform sending data of stream 1 and 3, until there is no data or window
func (m *streamsMap) RoundRobinSendingPrioritizeStream(fn streamLambdaSend, s *session, sch *scheduler) (bool, bool, bool, error) {
	for {
		allStreamNotExisted := true //true if all stream not existed
		notEmptyPackets := false    //true if exist one sent not empty packet
		hasWindows := false         //true if exist one has window

		for _, i := range []protocol.StreamID{1, 3} {
			notEmptyPacket, hasWindow, streamNotExist, err := m.iterateFuncPacketSend(i, fn)
			if err != nil && err != errMapAccess {
				return false, false, false, err
			}

			allStreamNotExisted = allStreamNotExisted && streamNotExist
			notEmptyPackets = notEmptyPackets || notEmptyPacket
			hasWindows = hasWindows || hasWindow
		}

		if !notEmptyPackets || !hasWindows || allStreamNotExisted {
			return notEmptyPackets, hasWindows, allStreamNotExisted, nil
		}

	}
}

func (m *streamsMap) RoundRobinIterate(fn streamLambda) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	numStreams := uint32(len(m.streams))
	startIndex := m.roundRobinIndex

	for _, i := range []protocol.StreamID{1, 3} {
		cont, err := m.iterateFunc(i, fn)
		if err != nil && err != errMapAccess {
			return err
		}
		if !cont {
			return nil
		}
	}

	for i := uint32(0); i < numStreams; i++ {
		streamID := m.openStreams[(i+startIndex)%numStreams]
		if streamID == 1 || streamID == 3 {
			continue
		}

		cont, err := m.iterateFunc(streamID, fn)
		if err != nil {
			return err
		}
		m.roundRobinIndex = (m.roundRobinIndex + 1) % numStreams
		if !cont {
			break
		}
	}
	return nil
}

// SHI: pop streamframe of streams reside in this path round-robinly
func (m *streamsMap) RoundRobinIteratePopOfPath(fn streamLambda, pth *path) error {
	//m.mutex.Lock()
	//defer m.mutex.Unlock()

	//only pop if there are streams on this path
	numStreamsOfPath := uint32(len(pth.streamIDs))
	startIndex := m.roundRobinIndexStream
	for i := uint32(0); i < numStreamsOfPath; i++ {
		sid := pth.streamIDs[(i+startIndex)%numStreamsOfPath]

		if sid == 1 || sid == 3 {
			continue
		}

		cont, err := m.iterateFunc(sid, fn)
		if err != nil && err != errMapAccess {
			return err
		}
		m.roundRobinIndexStream = (m.roundRobinIndexStream + 1) % numStreamsOfPath

		if !cont {
			return nil
		}

	}

	return nil

}

func fetchFlow(probability map[protocol.StreamID]float32) protocol.StreamID {
	maxInt := int(100000) //set range from 0-100000
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	randInt := r.Intn(maxInt)

	sumPro := float32(0)
	for sid := range probability {
		sumPro = sumPro + probability[sid]
		if float32(randInt) < float32(maxInt)*sumPro {
			return sid
		}
	}

	return 0
}

// SHI: pop streamframe of streams reside in this path (proportinally according to priority)
func (m *streamsMap) PriorityIteratePopOfPath(fn streamLambda, pth *path) error {
	// SHI:  calculate pop probability of each stream on this path based on priority
	m.mutex.Lock()
	defer m.mutex.Unlock()

	sum := float32(0)

	for i := 0; i < len(pth.streamIDs); i++ {
		sid := pth.streamIDs[i]
		// if utils.Debug() {
		// 	utils.Debugf("PriorityIteratePopOfPath: path %d assigned stream %d \n", pth.pathID, sid)
		// }
		// SHI: we prioritize stream 3 if either of them in this path, crypto stream (stream 1) is handled separately
		if sid == 3 {
			cont, err := m.iterateFunc(sid, fn)
			// if utils.Debug() {
			// 	utils.Debugf("PriorityIteratePopOfPath: path %d pop data of stream %d \n", sid)
			// }
			if err != nil && err != errMapAccess {
				return err
			}
			if !cont {
				return nil
			}
			continue
		}
		sum += float32(m.streams[sid].priority.Weight)

	}

	probability := make(map[protocol.StreamID]float32)

	for i := 0; i < len(pth.streamIDs); i++ {
		sid := pth.streamIDs[i]
		if sid == 1 || sid == 3 {
			continue
		}
		probability[sid] = float32(m.streams[sid].priority.Weight) / sum

		// if utils.Debug() {
		// 	utils.Debugf("SHI: The probability for stream %d on path %d to pop is %f", sid, pth.pathID, probability[sid])
		// }

	}

	cid := fetchFlow(probability)
	if cid == 0 {
		return errors.New("fail to select stream to pop")
	}
	// else {
	// 	if utils.Debug() {
	// 		utils.Debugf("PriorityIteratePopOfPath: path %d pop data of stream %d \n", cid)
	// 	}
	// }

	cont, err := m.iterateFunc(cid, fn)
	if err != nil && err != errMapAccess {
		return err
	}

	if !cont {
		return nil
	}

	return nil
}

// use m.roundRobinIndexSend because needed to resume packet sending from last stream
// avoid both using  m.roundRobinIndex with another function at the same time
func (m *streamsMap) RoundRobinIterateSend(fn streamLambdaSend, s *session, sch *scheduler) error {
	//m.mutex.Lock()
	//defer m.mutex.Unlock()
	for {
		numStreams := uint32(len(m.streams))
		startIndex := m.roundRobinIndexSend
		allStreamNotExisted := true
		notEmptyPackets := false
		hasWindows := false

		for _, i := range []protocol.StreamID{1, 3} {
			notEmptyPacket, hasWindow, streamNotExist, err := m.iterateFuncPacketSend(i, fn)
			if err != nil && err != errMapAccess {
				return err
			}

			allStreamNotExisted = allStreamNotExisted && streamNotExist
			notEmptyPackets = notEmptyPackets || notEmptyPacket
			hasWindows = hasWindows || hasWindow
		}

	NormalStreamLoop:
		for i := uint32(0); i < numStreams; i++ {
			streamID := m.openStreams[(i+startIndex)%numStreams]
			if streamID == 1 || streamID == 3 {
				continue NormalStreamLoop
			}

			notEmptyPacket, hasWindow, streamNotExist, err := m.iterateFuncPacketSend(streamID, fn)
			if err != nil {
				return err
			}
			m.roundRobinIndexSend = (m.roundRobinIndexSend + 1) % numStreams

			allStreamNotExisted = allStreamNotExisted && streamNotExist
			notEmptyPackets = notEmptyPackets || notEmptyPacket
			hasWindows = hasWindows || hasWindow

		}

		if allStreamNotExisted || !notEmptyPackets || !hasWindows {
			return nil
		}

	}
}

// SHI: implement sort interface to sort priority of streams

type order struct {
	Key   protocol.StreamID
	Value uint8
}

//sort existing stream id with priority descending order
func (m *streamsMap) sortStreamPriorityOrder() bool {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	var orders []order
	//get stream list to be scheduled
	streams := m.streamTree.schedule()

	if len(streams) != 0 {
		// clean result
		m.priorityOrder = nil
		orders = nil

		//every time extract streamID and its priority
		for _, str := range streams {
			// if utils.Debug() {
			// 	utils.Debugf("====== streamMap.streams: stream %d, priority %d, dependency %d, Exclusive %t\n", str.streamID, str.priority.Weight, str.priority.Dependency, str.priority.Exclusive)
			// }
			orders = append(orders, order{str.streamID, str.priority.Weight})
		}

		sort.Slice(orders, func(i, j int) bool {
			return orders[i].Value > orders[j].Value
		})

		for _, order := range orders {
			m.priorityOrder = append(m.priorityOrder, order.Key)
		}
		return true

	}
	return false

}

func (m *streamsMap) iterateFunc(streamID protocol.StreamID, fn streamLambda) (bool, error) {
	str, ok := m.streams[streamID]
	if !ok {
		return true, errMapAccess
	}
	return fn(str)
}

func (m *streamsMap) iterateFuncPacketSend(streamID protocol.StreamID, fn streamLambdaSend) (bool, bool, bool, error) {
	str, ok := m.streams[streamID]
	if !ok { //stream not existed
		return false, false, true, errMapAccess
	}
	return fn(str)
}

func (m *streamsMap) putStream(s *stream) error {
	id := s.StreamID()
	if _, ok := m.streams[id]; ok {
		return fmt.Errorf("a stream with ID %d already exists", id)
	}

	m.streams[id] = s
	m.openStreams = append(m.openStreams, id)
	if m.streamTree != nil {
		err := m.streamTree.addNode(s)
		if err != nil {
			return err
		}
	}
	return nil
}

// Attention: this function must only be called if a mutex has been acquired previously
// SHI: only called by server
func (m *streamsMap) RemoveStream(id protocol.StreamID) error {
	s, ok := m.streams[id]
	if !ok || s == nil {
		return fmt.Errorf("attempted to remove non-existing stream: %d", id)
	}

	if id%2 == 0 {
		m.numOutgoingStreams--
	} else {
		m.numIncomingStreams--
	}
	if utils.Debug() {
		utils.Debugf("RemoveStream remove stream %d", id)
	}
	for i, s := range m.openStreams {
		if s == id {
			// delete the streamID from the openStreams slice
			m.openStreams = m.openStreams[:i+copy(m.openStreams[i:], m.openStreams[i+1:])]
			// adjust round-robin index, if necessary
			if uint32(i) < m.roundRobinIndex {
				m.roundRobinIndex--
			}
			if uint32(i) < m.roundRobinIndexSend {
				m.roundRobinIndexSend--
			}
			break
		}
	}
	for i, s := range m.priorityOrder {
		if s == id {
			// delete the streamID from the priorityOrder slice
			m.priorityOrder = m.priorityOrder[:i+copy(m.priorityOrder[i:], m.priorityOrder[i+1:])]

			break
		}
	}

	delete(m.streams, id)

	m.openStreamOrErrCond.Signal()
	return nil
}

func (m *streamsMap) CloseWithError(err error) {
	m.mutex.Lock()
	defer m.mutex.Unlock()
	m.closeErr = err
	m.nextStreamOrErrCond.Broadcast()
	m.openStreamOrErrCond.Broadcast()
	for _, s := range m.openStreams {
		m.streams[s].Cancel(err)
	}
}
