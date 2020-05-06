#!/bin/bash

User="mininet"
Host="192.168.122.15"
SendDir="~/go/src/github.com/mkanakis/test-zmq/reply/"

scp interface.go pubsub.go test-reply.go zserver.go $User@$Host:$SendDir