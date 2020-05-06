package main

import zmq "github.com/pebbe/zmq4"

// BasicConfig ...
type BasicConfig struct {
	socket *zmq.Socket
	poller *zmq.Poller
}

// BasicOperations ...
type BasicOperations interface {
	NewConfig(zmq.Type, string) *zmq.Socket
	bind(string)
	Send(*Message) error
	RecvMessage() (*Message, error)
	Close()
}

// Message is a basic message struct
type Message struct {
	ID   int
	Data []string
}
