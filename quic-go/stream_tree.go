package quic

import (
	"fmt"
	"sync"

	"github.com/lucas-clemente/quic-go/internal/protocol"
	"github.com/lucas-clemente/quic-go/internal/utils"
)

type streamTree struct {
	root *node
	//toSend       *node
	openStreams  int
	nodeMap      map[protocol.StreamID]*node
	streamFramer *streamFramer
	blockedLast  bool

	sync.Mutex
}

// A Priority is a stream priority in QUIC
type Priority struct {
	Dependency protocol.StreamID
	Weight     uint8
	Exclusive  bool
}

type node struct {
	id              protocol.StreamID
	stream          *stream
	weight          uint8
	childrensWeight uint32
	state           uint8 //states: nodeIdle, nodeActive, nodeClosed
	activeChildren  uint16
	parent          *node
	children        []*node
	nextChild       uint16
	visited         bool //true if has been scheduled a path
}

const (
	nodeIdle uint8 = iota
	nodeActive
	nodeClosed
)

func newNode(id protocol.StreamID, stream *stream, parent *node) *node {
	return &node{
		id:      id,
		stream:  stream,
		weight:  protocol.DefaultStreamWeight,
		parent:  parent,
		state:   nodeActive,
		visited: false,
	}
}

func newStreamTree() *streamTree {
	nodeMap := make(map[protocol.StreamID]*node)

	return &streamTree{
		root:    newNode(0, nil, nil),
		nodeMap: nodeMap,
	}
}

func (n *node) deactivateNode() error {
	// if utils.Debug() {
	// 	utils.Debugf("streamTree.deactivateNode()\n")
	// }
	// Try to keep node around as long as possible in order to maintain priority information
	// since the priority of a node may be altered even after its stream has finished
	// Idle branches should be kept around for at least 2 RTTs

	n.state = nodeClosed
	n.stream = nil

	if n.parent != nil && n.activeChildren == 0 {
		n.parent.removeWeight(n)
	}

	return nil
}

func (n *node) setVisited() error {

	n.visited = true
	return nil
}

func (n *node) addWeight(child *node) {
	// if utils.Debug() {
	// 	utils.Debugf("streamTree.addWeight()\n")
	// }
	n.childrensWeight += uint32(child.weight) + 1
	n.activeChildren++
	n.children = append(n.children, child)

	if n.parent != nil && n.state != nodeActive && n.activeChildren == 1 {
		n.parent.addWeight(n)
	}
}

func (n *node) removeWeight(child *node) {
	// if utils.Debug() {
	// 	utils.Debugf("streamTree.removeWeight()\n")
	// }

	index := 0
	for i, c := range n.children {
		if c == child {
			index = i
			break
		}
	}
	n.children = append(n.children[:index], n.children[index+1:]...)
	if len(n.children) == 0 {
		n.nextChild = 0
	} else {
		n.nextChild = n.nextChild % uint16(len(n.children))
	}

	n.childrensWeight -= uint32(child.weight) - 1
	n.activeChildren--

	if n.parent != nil && n.activeChildren == 0 {
		n.parent.removeWeight(n)
	}
}

func (n *node) skip() {
	if n.parent != nil {
		n.parent.nextChild = (n.parent.nextChild + 1) % uint16(len(n.parent.children))
		n.parent.skip()
	}
}

// New nodes are intitially set to become the child of the root node
func (sch *streamTree) addNode(child *stream) error {
	sch.Lock()
	defer sch.Unlock()

	// if utils.Debug() {
	// 	utils.Debugf("streamTree.addNode()\n")
	// }

	if child == nil {
		return fmt.Errorf("attempt to add unknown node")
	}

	// root stream id = 0, root stream is nil
	//  header stream and crypto stream are treated the same as normal streams

	// if (child.streamID == 3 || child.streamID == 1) && sch.root.id != 0 {
	// 	sch.root.stream = child
	// 	sch.root.state = nodeActive
	// 	sch.root.id = child.streamID
	// 	sch.nodeMap[child.streamID] = sch.root
	// 	return nil
	// }

	// if utils.Debug() {
	// 	utils.Debugf("streamTree addNode(): stream %d, root %d\n", child.streamID, sch.root)
	// }
	n := newNode(child.streamID, child, sch.root)
	if n.state == nodeActive || n.id == 1 || n.id == 3 {
		sch.root.addWeight(n)
	}
	sch.nodeMap[child.streamID] = n

	return nil
}

func (sch *streamTree) maybeSetWeight(id protocol.StreamID, weight uint8) error {
	sch.Lock()
	defer sch.Unlock()

	// if utils.Debug() {
	// 	utils.Debugf("streamTree.maybeSetWeight()\n")
	// }

	if id == 1 || id == 3 /* Weight does not impact crypto and header stream */ {
		return nil
	}
	n, ok := sch.nodeMap[id]
	if !ok {
		return fmt.Errorf("setting weight of unknown stream %d", id)
	}
	if n.weight == weight {
		return nil
	}

	if n.state == nodeActive || n.activeChildren > 0 {
		diff := int(weight) - int(n.weight)
		newWeight := int(n.parent.childrensWeight) + diff
		n.parent.childrensWeight = uint32(newWeight)
	}

	n.weight = weight
	return nil
}

func (sch *streamTree) maybeSetParent(childID, parentID protocol.StreamID, exclusive bool) error {
	sch.Lock()
	defer sch.Unlock()

	// if utils.Debug() {
	// 	utils.Debugf("streamTree.maybeSetParent()\n")
	// }

	if childID == parentID {
		return fmt.Errorf("setting stream %d as its own parent", childID)
	}
	if childID == 1 {
		return fmt.Errorf("setting parent of crypto stream")
	}
	if childID == 3 {
		return fmt.Errorf("setting parent of header stream")
	}
	if parentID == 1 {
		return fmt.Errorf("setting parent to crypto stream")
	}
	if parentID == 3 {
		parentID = 0 // Is it really necessary that the root node has ID 0?
	}
	child, ok := sch.nodeMap[childID]
	if !ok {
		return fmt.Errorf("setting unknown stream %d as exclusive child of stream %d", childID, parentID)
	}
	if !exclusive && child.parent != nil && child.parent.id == parentID /* Already parent, nothing to do */ {
		return nil
	}
	newParent, ok := sch.nodeMap[parentID]
	if !ok {
		return fmt.Errorf("setting stream %d as exclusive child of unknown stream %d", childID, parentID)
	}
	oldParent := child.parent

	// RFC 7540: If a stream is made dependent on one of its own dependencies, the
	// formerly dependent stream is first moved to be dependent on the
	// reprioritized stream's previous parent.  The moved dependency retains
	// its weight.
	for n := newParent.parent; n.parent != nil; n = n.parent {
		if n == child {
			if newParent.state == nodeActive || newParent.activeChildren > 0 {
				// Only active nodes are set as children
				newParent.parent.removeWeight(newParent)
				if oldParent != nil {
					oldParent.addWeight(newParent)
				}
			}
			newParent.parent = oldParent
		}
	}

	// Remove node from its previous parent
	if child.parent != nil {
		if child.state == nodeActive || child.activeChildren > 0 {
			child.parent.removeWeight(child)
		}

		child.parent = nil
	}

	// RFC 7540: Setting a dependency with the exclusive flag for a
	// reprioritized stream causes all the dependencies of the new parent
	// stream to become dependent on the reprioritized stream.
	if exclusive {
		for _, c := range newParent.children {
			if c != newParent {
				if c.state == nodeActive || c.activeChildren > 0 {
					child.addWeight(c)
					newParent.removeWeight(c)
				}

				c.parent = child
			}
		}
	}

	child.parent = newParent
	if child.state == nodeActive || child.activeChildren > 0 {
		newParent.addWeight(child)
	}

	return nil
}

func (sch *streamTree) setActive(id protocol.StreamID) error {
	sch.Lock()
	defer sch.Unlock()

	if id == 1 /* Crypto stream handled separatly */ {
		return nil
	}
	if id == 3 /* Header stream is always considered active */ {
		return nil
	}

	n, ok := sch.nodeMap[id]
	if !ok {
		return fmt.Errorf("setting unknown stream %d active", id)
	}

	n.state = nodeActive
	n.parent.addWeight(n)
	sch.openStreams++

	return nil
}

//return all streams
func (sch *streamTree) traverseAll(n *node) (strm []*node) {
	// if utils.Debug() {
	// 	utils.Debugf("streamTree.traverseAll(): Visit %d\n", n.id)
	// }

	if n.stream != nil && n.stream.finishedWriteAndSentFin() {
		sch.openStreams--
		n.deactivateNode()
	}

	if n.stream != nil {
		strm = append(strm, n)

	}

	if n.activeChildren > 0 {
		//traverse child
		for i := 0; i < len(n.children); i++ {
			c := n.children[n.nextChild]
			strm = append(strm, sch.traverseAll(c)...)
			n.nextChild = (n.nextChild + 1) % uint16(len(n.children))

		}

	}

	return
}

//return  streams for path scheduling
// only unvisited and Dependent stream(the dependency is removed by finish sending of parent stream)
func (sch *streamTree) traverse(n *node) (strm []*node) {
	// if utils.Debug() {
	// 	utils.Debugf("streamTree.traverse(): Visit %d\n", n.id)
	// }

	if n.stream != nil && n.stream.finishedWriteAndSentFin() {
		sch.openStreams--
		n.deactivateNode()
	}
	if n.stream != nil && n.stream.checksize {
		n.setVisited()
	}

	if !n.visited && n.stream != nil {

		// handle visited streams
		// if n.id == 1 || n.id == 3 /* Special case for crypto and header stream, since they never close */ {
		// 	strm = append(strm, n)
		// 	n.setVisited()
		// } else
		if n.state == nodeActive {
			strm = append(strm, n)
		}

	} else if n.activeChildren > 0 {
		if n.stream == nil || (n.stream != nil && (n.stream.finishedWriteAndSentFin() || n.id == 1 || n.id == 3)) {
			for i := 0; i < len(n.children); i++ {
				c := n.children[n.nextChild]
				strm = append(strm, sch.traverse(c)...)

			}
		}
	}
	if n.parent != nil && len(n.parent.children) > 0 {
		n.parent.nextChild = (n.parent.nextChild + 1) % uint16(len(n.parent.children))
	}
	return
}

func (sch *streamTree) schedule() []*stream {
	sch.Lock()
	defer sch.Unlock()

	nodes := sch.traverse(sch.root)

	var streams []*stream
	for _, node := range nodes {
		streams = append(streams, node.stream)

	}
	return streams
}
func (sch *streamTree) scheduleAll() []*stream {
	sch.Lock()
	defer sch.Unlock()

	nodes := sch.traverseAll(sch.root)

	var streams []*stream
	for _, node := range nodes {
		streams = append(streams, node.stream)

	}
	return streams
}

//printTree print all nodes with level order
func (sch *streamTree) printTree() {

	var dfs func(*node, uint32, map[protocol.StreamID]uint32)

	dfs = func(n *node, level uint32, res map[protocol.StreamID]uint32) {

		if n.stream != nil {
			res[n.id] = level

		}

		if n.activeChildren > 0 {
			//traverse child
			for i := 0; i < len(n.children); i++ {
				c := n.children[n.nextChild]
				dfs(c, level+1, res)
				n.nextChild = (n.nextChild + 1) % uint16(len(n.children))

			}
		}

		return

	}

	res := make(map[protocol.StreamID]uint32)
	dfs(sch.root, 0, res)
	if utils.Debug() {
		utils.Debugf("print out StreamTree:\n")
	}
	for k, v := range res {
		if utils.Debug() {
			utils.Debugf("streamID: %d, level %d\n", k, v)
		}
	}

}
