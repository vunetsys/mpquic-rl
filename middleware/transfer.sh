#!/bin/bash

User="mininet"
Host="192.168.122.157"
SendDir="~/go/src/github.com/mkanakis/middleware/"

scp interface.go pubsub.go middleware.go zserver.go $User@$Host:$SendDir
