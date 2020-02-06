package quic

import (
	"errors"

	"github.com/lucas-clemente/quic-go/internal/protocol"
)

//StreamToPath stores scheduling results of stream to path. A stream can be scheduled onto multiple paths
type StreamToPath map[protocol.StreamID][]protocol.PathID

//Add adds a item to streamToPath and avoid duplicate
func (streamToPath StreamToPath) Add(sid protocol.StreamID, pid protocol.PathID) error {

	if len(streamToPath[sid]) == 0 {
		streamToPath[sid] = []protocol.PathID{pid}
	} else {
		dup, err := streamToPath.Find(sid, pid)
		if err != nil {
			return err
		}
		if !dup {
			streamToPath[sid] = append(streamToPath[sid], pid)
		}
	}
	return nil
}

//Find checks whether the entry is contained in streamToPath
func (streamToPath StreamToPath) Find(sid protocol.StreamID, pid protocol.PathID) (bool, error) {
	if streamToPath == nil {
		return false, errors.New("streamToPath is nil")
	}
	values := streamToPath[sid]
	find := false

	for i := 0; i >= 0 && i < len(values); i++ {
		if values[i] == pid {
			find = true
			break
		}

	}
	return find, nil
}

//Get returns the scheduled path IDs of stream i
func (streamToPath StreamToPath) Get(i protocol.StreamID) ([]protocol.PathID, error) {
	if streamToPath == nil {
		return nil, errors.New("streamToPath is nil")
	}
	values := streamToPath[i]
	if len(values) == 0 {
		return nil, errors.New("streamToPath record of this stream not found")
	}
	return values, nil
}

//DeleteOne deletes a item from streamToPath
func (streamToPath StreamToPath) DeleteOne(i protocol.StreamID, value protocol.PathID) error {
	if streamToPath == nil {
		return errors.New("streamToPath is nil")
	}
	values := streamToPath[i]
	if len(streamToPath) == 0 || len(values) == 0 {
		return errors.New("nothing to delete")
	}
	delete(streamToPath, i)

	find := false
	// delete record in pth.streamIDs
	for j := 0; j >= 0 && j < len(values); j++ {
		tmp := values[j]
		if tmp == value {
			values = append(values[:j], values[j+1:]...)
			find = true
			j--
		} else {
			streamToPath.Add(i, tmp)
		}

	}
	if !find {
		return errors.New("nothing to delete")
	}
	return nil
}

//Delete deletes all record of stream i from streamToPath
func (streamToPath StreamToPath) Delete(i protocol.StreamID) error {
	if streamToPath == nil {
		return errors.New("streamToPath is nil")
	}
	values := streamToPath[i]
	if len(streamToPath) == 0 || len(values) == 0 {
		return errors.New("nothing to delete")
	}
	delete(streamToPath, i)

	return nil
}
