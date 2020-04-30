package main

import (
	"fmt"

	zmq "github.com/pebbe/zmq4"
)

func main() {
	server := NewServer(zmq.REP, "ipc:///tmp/zmq")
	client := NewServer(zmq.REQ, "tcp://*:5555")

	request := &Message{}
	response := &Message{}
	var err error

	// Request - RecvMessage are blocking methods
	for {
		// Get initial request from GOServer
		request, err = server.RecvMessage()

		if err != nil {
			fmt.Println(err.Error())
			break
		}

		// PASS on request to agent
		err = client.Request(request)
		if err != nil {
			fmt.Println(err.Error())
			break
		}

		// Get response from agent
		response, err = client.RecvMessage()
		if err != nil {
			fmt.Println(err.Error())
			break
		}

		// Forward response back to GOServer
		err = server.Request(response)
		if err != nil {
			fmt.Println(err.Error())
			break
		}
	}

	server.Close()
	client.Close()

	fmt.Println("W: interrupted")
}
