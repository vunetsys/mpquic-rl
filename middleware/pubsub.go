package main

import (
	"fmt"
	"strconv"

	zmq "github.com/pebbe/zmq4"
)

// PubSub ...
type PubSub = BasicConfig

// Message ...
// type Message struct {
// 	ID   int
// 	Data []string
// }

// NewConfig instantiates a new server
func NewConfig(servertype zmq.Type, endpoint string) (pubsub *PubSub) {
	pubsub = &BasicConfig{}
	var err error

	pubsub.socket, err = zmq.NewSocket(servertype)
	pubsub.bind(endpoint)

	if err != nil {
		fmt.Println(err.Error())
	}

	pubsub.poller = zmq.NewPoller()
	pubsub.poller.Add(pubsub.socket, zmq.POLLIN)

	return
}

// Bind to an endpoint
func (pubsub *PubSub) bind(endpoint string) {
	err := pubsub.socket.Bind(endpoint)

	if err != nil {
		fmt.Println(err.Error())
	}
}

// Close ...
func (pubsub *PubSub) Close() {
	pubsub.Close()
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
	}
	return
}
