#!/bin/bash

User="mininet"
Host="192.168.122.15"
SendDir="~/go/src/github.com/lucas-clemente/quic-go/"

scp scheduler.go $User@$Host:$SendDir
scp zclient.go $User@$Host:$SendDir
# scp congestion/bdw_stats.go $User@$Host:$SendDir/congestion 
