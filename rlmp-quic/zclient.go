package quic

import (
	"bytes"
	"encoding/json"
	"errors"
	"strconv"
	"time"

	"github.com/lucas-clemente/quic-go/internal/protocol"
	"github.com/lucas-clemente/quic-go/internal/utils"
	zmq "github.com/pebbe/zmq4"
)

const (
	globalTimeout  = 2500 * time.Millisecond
	requestTimeout = 50 * time.Millisecond
	maxRetries     = 3 // before we abandon
)

// ZClient ZMQ-Client
type ZClient struct {
	socket   *zmq.Socket
	poller   *zmq.Poller
	sequence uint64
}

// Bandwidth same as bandwidth.go

// PathStats combined
type PathStats struct {
	PathID          uint8
	SmoothedRTT     float64 // in seconds, if wanted in ms use time.Duration
	Bandwidth       uint64
	Packets         uint64
	Retransmissions uint64
	Losses          uint64
}

// Request ...
type Request struct {
	StreamID    protocol.StreamID
	RequestPath string
	Path1       *PathStats
	Path2       *PathStats
}

// Response ...
type Response struct {
	StreamID protocol.StreamID
	PathID   uint8
}

// NewClient instantiates a new zmq.Request client and a zmq.Poller
func NewClient() (client *ZClient) {
	client = &ZClient{}
	var err error

	client.socket, err = zmq.NewSocket(zmq.REQ)

	if err != nil {
		utils.Errorf(err.Error())
	}

	client.poller = zmq.NewPoller()
	client.poller.Add(client.socket, zmq.POLLIN)

	return
}

// Connect ...
func (client *ZClient) Connect(endpoint string) {
	err := client.socket.Connect(endpoint)

	if err != nil {
		utils.Errorf("Error connecting")
		utils.Errorf(err.Error())
	}
}

// Bind ...
func (client *ZClient) Bind(endpoint string) {
	err := client.socket.Bind(endpoint)

	if err != nil {
		utils.Errorf("Error Binding")
		utils.Errorf(err.Error())
	}
}

// Close ...
func (client *ZClient) Close() {
	client.Close()
}

// Response ...
func (client *ZClient) Response() (response *Response, err error) {
	response = &Response{}
	reply := []string{}

	endtime := time.Now().Add(globalTimeout)

	for time.Now().Before(endtime) {
		polled, err := client.poller.Poll(endtime.Sub(time.Now()))
		if err == nil && len(polled) > 0 {
			// reply
			reply, _ = client.socket.RecvMessage(0)
			if len(reply) != 2 {
				panic("len(reply) != 2")
			}

			cstrID, _ := strconv.ParseUint(reply[0], 10, 8) // don't care about the error thug life
			response.StreamID = protocol.StreamID(cstrID)
			// response.PathID = reply[1:]
			// pathID, cerr := strconv.ParseUint(reply[1], 10, 8)
			var pathID uint64
			pathID, err = strconv.ParseUint(reply[1], 10, 8)
			// This conversion is safe!
			response.PathID = uint8(pathID)
			break
		}
	}

	if len(reply) == 0 {
		err = errors.New("No Reply")
	}
	return
}

// Request ...
func (client *ZClient) Request(request *Request) (err error) {
	utils.Infof("ID %d, pathID %s, bandwidth %d, smoothedRTT %d, packets %d, retransmissions %d, losses %d, rpath: %s\n",
		request.StreamID,
		request.Path1.PathID,
		request.Path1.Bandwidth,
		request.Path1.SmoothedRTT,
		request.Path1.Packets,
		request.Path1.Retransmissions,
		request.Path1.Losses,
		request.RequestPath)

	utils.Infof("ID %d, pathID %s, bandwidth %d, smoothedRTT %d, packets %d, retransmissions %d, losses %d, rpath: %s\n",
		request.StreamID,
		request.Path2.PathID,
		request.Path2.Bandwidth,
		request.Path2.SmoothedRTT,
		request.Path2.Packets,
		request.Path2.Retransmissions,
		request.Path2.Losses,
		request.RequestPath)

	// first we have to pack our struct into json -> []byte
	packedRequest := new(bytes.Buffer)
	json.NewEncoder(packedRequest).Encode(request)

	bsent, err := client.socket.SendMessage(request.StreamID, packedRequest.Bytes())
	if err != nil || bsent <= 0 {
		utils.Errorf("Error in Sending Request\n")
		utils.Errorf(err.Error())
	}

	return err
}
