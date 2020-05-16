#!/bin/bash

User="mininet"
Host="192.168.122.157"
SendDir="~/go/src/github.com/lucas-clemente/quic-go/"

scp scheduler.go $User@$Host:$SendDir
scp zclient.go $User@$Host:$SendDir
scp zpublisher.go $User@$Host:$SendDir


# scp example/client_browse_deptree/zpublisher.go $User@$Host:$SendDir/example/client_browse_deptree/
scp example/client_browse_deptree/main.go $User@$Host:$SendDir/example/client_browse_deptree/
# scp example/main.go $User@$Host:$SendDir/example/


# scp congestion/bdw_stats.go $User@$Host:$SendDir/congestion 

# Add PATH to stream
scp session.go $User@$Host:$SendDir
scp stream.go $User@$Host:$SendDir
scp h2quic/server.go $User@$Host:$SendDir/h2quic/