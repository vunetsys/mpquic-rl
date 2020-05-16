## Marios Evangelos Kanakis - MSc Thesis Project

## DRL Scheduler for MP-QUIC protocol

### Instalation Guide (WIP)

* Grab the original MP-QUIC VM image from https://multipath-quic.org/2017/12/09/artifacts-available.html 

* Start up the VM  with KEMU

* SSH Into the VM (user: mininet, pass: mininet)

* Place your ssh public keys under ~/.ssh/authorized_keys (from link above this is step 3 from end)

* From 'our' repo, copy the contents of 'minitopo/' under VM's '~/git/minitopo/src/'

* Move (as in mv) the original quic-go directory under '~/go/src/github.com/lucas-clemente/quic-go/' to '~/go/src/github.com/lucas-clemente/mp-quic'

* Under the original '~/go/src/github.com/lucas-clemente/quic-go/' copy all contents of 'mpquic-rl' from the repo

* Under '~/go/src/github.com/mkanakis/test-zmq/reply/' place the contents of dir 'middleware' (This path will change in a subsequent version)

* Create a directory 'client' under '~/go/src/github.com/lucas-clemente/'

* Inside the client directory copy the folder 'dependency_graphs'

* Create a directory 'server' under '~/go/src/github.com/lucas-clemente/'

* Inside the server directory extract the server.tar.gz with the missing and pages directories -> downloaded from here http://wprof.cs.washington.edu/spdy/tool/ (in the section 'Dependency Graph')

* Everytime you start up the VM, remember to run the './mount_tmpfs.sh' under '~/' 
