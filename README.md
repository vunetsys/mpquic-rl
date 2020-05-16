## Marios Evangelos Kanakis - MSc Thesis Project

## DRL Scheduler for MP-QUIC protocol

### Instalation Guide (WIP)

Following steps are the initial VM setup for running any kind of experiments with Multipath QUIC protocol, courtesy of the original MP-QUIC authors (put refs;). The environment/experiments setup is from PStream (put refs;), as well as the stream scheduling code (`mpquic-rl`) which is used as the basis for building our RL agent.

The list should be sufficient to get you started on the VM and the projects' structure but is not __*runnable complete*__. 

__*Information*__ on how to run the agent, should be available under `central_service/README.md`.

_Steps_:

  1. Grab the original MP-QUIC VM image from https://multipath-quic.org/2017/12/09/artifacts-available.html 

  2. Start up the VM  with KEMU

  3. SSH Into the VM (user: mininet, pass: mininet)

  4. Place your ssh public keys under ~/.ssh/authorized_keys (from link above this is step 3 from end)

  5. From 'our' repo, copy the contents of 'minitopo/' under VM's '~/git/minitopo/src/'

  6. Move (as in mv) the original quic-go directory under '~/go/src/github.com/lucas-clemente/quic-go/' to  '~/go/src/github.com/lucas-clemente/mp-quic'

  7. Under the original '~/go/src/github.com/lucas-clemente/quic-go/' copy all contents of 'mpquic-rl' from the repo

  8. Under '~/go/src/github.com/mkanakis/test-zmq/reply/' place the contents of dir 'middleware' (This path will change in a subsequent version)

  9. Create a directory 'client' under '~/go/src/github.com/lucas-clemente/'

  10. Inside the client directory copy the folder 'dependency_graphs'

  11. Create a directory 'server' under '~/go/src/github.com/lucas-clemente/'

  12. Inside the server directory extract the server.tar.gz with the missing and pages directories -> downloaded from here http://wprof.cs.washington.edu/spdy/tool/ (in the section 'Dependency Graph')

  13. Everytime you start up the VM, remember to run the './mount_tmpfs.sh' under '~/' 
