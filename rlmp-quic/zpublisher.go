package quic

import (
	"bytes"
	"encoding/json"

	"github.com/lucas-clemente/quic-go/internal/utils"
	zmq "github.com/pebbe/zmq4"
)

// ZPublisher ZMQ-Client
type ZPublisher struct {
	socket   *zmq.Socket
	poller   *zmq.Poller
	sequence uint64
}

// Bandwidth same as bandwidth.go

// StreamInfo combined
type StreamInfo struct {
	StreamID       uint32
	ObjectID       string
	CompletionTime float64
	// StartTime  time.Time
	// EndTime    time.Time
}

// NewPublisher instantiates a new zmq.Publisher and a zmq.Poller
func NewPublisher() (publisher *ZPublisher) {
	publisher = &ZPublisher{}
	var err error

	publisher.socket, err = zmq.NewSocket(zmq.PUB)

	if err != nil {
		utils.Errorf(err.Error())
	}

	publisher.poller = zmq.NewPoller()
	publisher.poller.Add(publisher.socket, zmq.POLLIN)

	return
}

// Connect ..
func (publisher *ZPublisher) Connect(endpoint string) {
	err := publisher.socket.Connect(endpoint)

	if err != nil {
		utils.Errorf("Error connecting")
		utils.Errorf(err.Error())
	}
}

// Bind ...
func (publisher *ZPublisher) Bind(endpoint string) {
	err := publisher.socket.Bind(endpoint)

	if err != nil {
		utils.Errorf("Error Binding")
		utils.Errorf(err.Error())
	}
}

// Close ...
func (publisher *ZPublisher) Close() {
	publisher.Close()
}

// Publish messages so everyone listening can receive
func (publisher *ZPublisher) Publish(streamInfo *StreamInfo) (err error) {
	utils.Infof("StreamID %d, ObjectID: %s, CompletionTime: %d\n",
		streamInfo.StreamID,
		streamInfo.ObjectID,
		streamInfo.CompletionTime)

	// first we have to pack our struct into json -> []byte
	packedMessage := new(bytes.Buffer)
	json.NewEncoder(packedMessage).Encode(streamInfo)

	bsent, err := publisher.socket.SendMessage(streamInfo.StreamID, packedMessage.Bytes())
	if err != nil || bsent <= 0 {
		utils.Errorf("Error in publishing message\n")
		utils.Errorf(err.Error())
	}

	return err
}
