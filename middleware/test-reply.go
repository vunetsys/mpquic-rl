package main

import (
	"fmt"
	"sync"

	zmq "github.com/pebbe/zmq4"
)

func listenAndForward(wg *sync.WaitGroup) {
	server := NewServer(zmq.REP, "ipc:///tmp/zmq")
	client := NewServer(zmq.REQ, "tcp://*:5555")
	request := &Message{}
	response := &Message{}
	var err error

	defer server.Close()
	defer client.Close()
	defer wg.Done()

	fmt.Println("ListenAndForward")

	var loopCounter int = 0

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

		loopCounter++
		fmt.Println("LAF: ", loopCounter)
	}

}

func subscribeAndForward(wg *sync.WaitGroup) {
	subscriber := NewConfig(zmq.SUB, "ipc:///tmp/zmqpubsub")
	publisher := NewConfig(zmq.PUB, "tcp://*:5556")
	message := &Message{}
	var err error

	// subscribe to all
	subscriber.socket.SetSubscribe("")

	defer subscriber.Close()
	defer publisher.Close()
	defer wg.Done()

	fmt.Println("SubscribeAndForward")

	var loopCounter int = 0

	for {
		message, err = subscriber.RecvMessage()
		if err != nil {
			fmt.Println(err.Error())
			break
		}

		err = publisher.Send(message)
		if err != nil {
			fmt.Println(err.Error())
			break
		}

		loopCounter++
		fmt.Println("SAF: ", loopCounter)
	}
}

func main() {
	var wg sync.WaitGroup

	go listenAndForward(&wg)
	wg.Add(1)
	go subscribeAndForward(&wg)
	wg.Add(1)

	wg.Wait()
}

// func main() {
// 	server := NewServer(zmq.REP, "ipc:///tmp/zmq")
// 	client := NewServer(zmq.REQ, "tcp://*:5555")

// 	request := &Message{}
// 	response := &Message{}
// 	var err error

// 	// Request - RecvMessage are blocking methods
// 	for {
// 		// Get initial request from GOServer
// 		request, err = server.RecvMessage()

// 		if err != nil {
// 			fmt.Println(err.Error())
// 			break
// 		}

// 		// PASS on request to agent
// 		err = client.Request(request)
// 		if err != nil {
// 			fmt.Println(err.Error())
// 			break
// 		}

// 		// Get response from agent
// 		response, err = client.RecvMessage()
// 		if err != nil {
// 			fmt.Println(err.Error())
// 			break
// 		}

// 		// Forward response back to GOServer
// 		err = server.Request(response)
// 		if err != nil {
// 			fmt.Println(err.Error())
// 			break
// 		}
// 	}

// 	server.Close()
// 	client.Close()

// 	fmt.Println("W: interrupted")
// }
