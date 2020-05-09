package main

import (
	"fmt"
	"strconv"
	"time"

	zmq "github.com/pebbe/zmq4"
)

const (
	globalTimeout  = 2500 * time.Millisecond
	requestTimeout = 10 * time.Millisecond
	maxRetries     = 3 // before we abandon
)

// ZServer ...
type ZServer struct {
	socket *zmq.Socket
	poller *zmq.Poller
}

// Message ...
// type Message struct {
// 	ID   int
// 	Data []string
// }

// NewServer instantiates a new server
func NewServer(servertype zmq.Type, endpoint string) (s *ZServer) {
	s = &ZServer{}
	var err error

	s.socket, err = zmq.NewSocket(servertype)
	s.bind(endpoint)

	if err != nil {
		fmt.Println(err.Error())
	}

	s.poller = zmq.NewPoller()
	s.poller.Add(s.socket, zmq.POLLIN)

	return
}

// Bind to an endpoint
func (s *ZServer) bind(endpoint string) {
	err := s.socket.Bind(endpoint)

	if err != nil {
		fmt.Println(err.Error())
	}
}

// Close ...
func (s *ZServer) Close() {
	s.socket.Close()
}

// Request sends a message
func (s *ZServer) Request(request *Message) (err error) {
	bsent, err := s.socket.SendMessage(request.ID, request.Data)

	if err != nil || bsent == 0 {
		fmt.Println(err.Error())
	}
	return
}

// RecvMessage polls and receives a message
func (s *ZServer) RecvMessage() (request *Message, err error) {
	request = &Message{}
	rawRequest := []string{}

	for {
		polled, err := s.poller.Poll(requestTimeout)
		//fmt.Println("zserver polling")
		if err == nil && len(polled) > 0 {
			// reply
			rawRequest, _ = s.socket.RecvMessage(0)
			if len(rawRequest) != 2 {
				panic("len(reply) != 2")
			}

			request.ID, _ = strconv.Atoi(rawRequest[0])
			request.Data = rawRequest[1:]
			break
		}
		//time.Sleep(10 * time.Millisecond)
	}
	return
}
