package main

import (
	"flag"
	"fmt"
	"sync"

	zmq "github.com/pebbe/zmq4"
)

func listenAndForward(serverAddrs *string, clientAddrs *string, wg *sync.WaitGroup) {
	server := NewServer(zmq.REP, *serverAddrs)
	client := NewServer(zmq.REQ, *clientAddrs)

	request := &Message{}
	response := &Message{}
	var err error

	defer server.Close()
	defer client.Close()
	defer wg.Done()

	fmt.Println("ListenAndForward")

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
}

func subscribeAndForward(pubAddrs *string, subAddrs *string, wg *sync.WaitGroup) {
	publisher := NewConfig(zmq.PUB, *pubAddrs)
	subscriber := NewConfig(zmq.SUB, *subAddrs)

	message := &Message{}
	var err error

	// subscribe to all
	subscriber.socket.SetSubscribe("")

	defer subscriber.Close()
	defer publisher.Close()
	defer wg.Done()

	fmt.Println("SubscribeAndForward")

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
	}
}

func main() {
	server := flag.String("sv", "ipc:///tmp/zmq", "Server listenAndForward")
	client := flag.String("cl", "tcp://*:5555", "Client listenAndForward")
	publisher := flag.String("pub", "tcp://*:5556", "Publisher Subscribe&Forward")
	subscriber := flag.String("sub", "ipc:///tmp/pubsub", "Subscriber Subscribe&Forward")

	flag.Parse()

	fmt.Println(*server)
	fmt.Println(*client)
	fmt.Println(*publisher)
	fmt.Println(*subscriber)

	var wg sync.WaitGroup

	go listenAndForward(server, client, &wg)
	wg.Add(1)
	go subscribeAndForward(publisher, subscriber, &wg)
	wg.Add(1)

	wg.Wait()
}
