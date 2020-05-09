package quic

import (
	"bytes"
	"encoding/json"
	"errors"
	"time"

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
	Path           string
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

	publisher.setLingerInfinite()

	publisher.poller = zmq.NewPoller()
	publisher.poller.Add(publisher.socket, zmq.POLLIN)

	return
}

// setLingerInfinite ..
func (publisher *ZPublisher) setLingerInfinite() {
	if err := publisher.socket.SetLinger(-1); err != nil {
		panic("Cannot set Linger to infinite")
	}
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
	publisher.socket.Close()
}

// Publish messages so everyone listening can receive
func (publisher *ZPublisher) Publish(streamInfo *StreamInfo) (err error) {
	utils.Infof("StreamID %d, ObjectID: %s, CompletionTime: %d, Path: %s\n",
		streamInfo.StreamID,
		streamInfo.ObjectID,
		streamInfo.CompletionTime,
		streamInfo.Path)

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

// RecvConfirmation ...
func (publisher *ZPublisher) RecvConfirmation() (err error) {
	reply := []string{}

	endtime := time.Now().Add(globalTimeout)

	for {
		polled, err := publisher.poller.Poll(endtime.Sub(time.Now()))
		if err == nil && len(polled) > 0 {
			// reply
			reply, _ = publisher.socket.RecvMessage(0)
			if len(reply) != 2 {
				panic("len(reply) != 2")
			}

			break
		}
	}

	if len(reply) == 0 {
		err = errors.New("No Reply")
	}
	return
}
