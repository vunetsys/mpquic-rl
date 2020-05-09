package main

import (
	"fmt"
	"strconv"

	zmq "github.com/pebbe/zmq4"
)

// PubSub ...
type PubSub = BasicConfig

// NewConfig instantiates a new server
func NewConfig(servertype zmq.Type, endpoint string) (pubsub *PubSub) {
	pubsub = &BasicConfig{}
	var err error

	pubsub.socket, err = zmq.NewSocket(servertype)

	if err != nil {
		fmt.Println("Error in NewSocket")
		fmt.Println(err.Error())
	}

	pubsub.bind(endpoint)
	pubsub.setLingerInfinite()

	pubsub.poller = zmq.NewPoller()
	pubsub.poller.Add(pubsub.socket, zmq.POLLIN)

	return
}

// SetLingerInfinite
func (pubsub *PubSub) setLingerInfinite() {
	pubsub.socket.SetLinger(-1)
}

// Bind to an endpoint
func (pubsub *PubSub) bind(endpoint string) {
	err := pubsub.socket.Bind(endpoint)

	if err != nil {
		fmt.Println("Error binding")
		fmt.Println(err.Error())
	}
}

// Close ...
func (pubsub *PubSub) Close() {
	pubsub.socket.Close()
}

// Send sends a message
func (pubsub *PubSub) Send(message *Message) (err error) {
	bsent, err := pubsub.socket.SendMessage(message.ID, message.Data)

	if err != nil || bsent == 0 {
		fmt.Println(err.Error())
	}
	return
}

// RecvMessage polls and receives a message
func (pubsub *PubSub) RecvMessage() (message *Message, err error) {
	message = &Message{}
	rawMessage := []string{}

	for {
		polled, err := pubsub.poller.Poll(requestTimeout)
		//fmt.Println("subscriber polling")
		if err == nil && len(polled) > 0 {
			// reply
			rawMessage, _ = pubsub.socket.RecvMessage(0)
			if len(rawMessage) != 2 {
				panic("len(reply) != 2")
			}

			message.ID, _ = strconv.Atoi(rawMessage[0])
			message.Data = rawMessage[1:]
			break
		}
		//time.Sleep(10 * time.Millisecond)
	}
	return
}
