#! /usr/bin/python

from __future__ import print_function

# Doing * imports is bad :'(
from core.generate_topo import *
from core.generate_xp import *

import core.core as core
import numpy as np
import os

REMOTE_SERVER_RUNNER_HOSTNAME = ["mininet@127.0.0.1"]
REMOTE_SERVER_RUNNER_PORT = ["3022"]


def getPostProcessingList(**kwargs):
    toReturn = []
    topoBasename = os.path.basename(kwargs["topoAbsPath"])
    # toReturn.append(("client.pcap",
    #                  "_".join([str(x) for x in [kwargs["testDirectory"], kwargs["xp"], kwargs["protocol"], kwargs["multipath"],
    #                                             topoBasename, "client.pcap"]])))
    # toReturn.append(("server.pcap",
    #                  "_".join([str(x) for x in [kwargs["testDirectory"], kwargs["xp"], kwargs["protocol"], kwargs["multipath"],
    #                                             topoBasename, "server.pcap"]])))
    toReturn.append(("command.log", "command.log"))
    toReturn.append(("ping.log", "ping.log"))
    if kwargs["xp"] == HTTPS:
        toReturn.append(("https_client.log", "https_client.log"))
        toReturn.append(("https_server.log", "https_server.log"))
    else:
        toReturn.append(("quic_client.log", "quic_client.log"))
        toReturn.append(("quic_server.log", "quic_server.log"))

    toReturn.append(("netstat_client_before", "netstat_client_before"))
    toReturn.append(("netstat_server_before", "netstat_server_before"))
    toReturn.append(("netstat_client_after", "netstat_client_after"))
    toReturn.append(("netstat_server_after", "netstat_server_after"))

    return toReturn


def quicTests(topos, protocol="mptcp", tmpfs="/mnt/tmpfs"):
    experienceLauncher = core.ExperienceLauncher(REMOTE_SERVER_RUNNER_HOSTNAME, REMOTE_SERVER_RUNNER_PORT)

    def testsXp(**kwargs):
        def testsMultipath(**kwargs):
            def test(**kwargs):
                xpDict = {
                    XP_TYPE: kwargs["xp"],
                    SCHEDULER_CLIENT: "default",
                    SCHEDULER_SERVER: "default",
                    CC: "olia" if kwargs["multipath"] == 1 else "cubic",
                    CLIENT_PCAP: "yes",
                    SERVER_PCAP: "yes",
                    HTTPS_FILE: "random",
                    PROJECT: "mp-quic",     # quic-go is the prioritized stream scheduling project, mp-quic is the original multipath-quic project
                    HTTPS_RANDOM_SIZE: "10",  #default to PRIORITY_HIGH
                    PRIORITY_HIGH: "200",   # quic-go priority seting: uint8 type from 1 to 255
                    HTTPS_RANDOM_SIZE2: "20000",
                    PRIORITY_LOW: "10",     # quic-go priority seting
                    MULTIFILE: "0", #default 0
                    HTTPS_RANDOM_SIZE3: "100",
                    PRIORITY_3:"150",
                    HTTPS_RANDOM_SIZE4: "15000",
                    PRIORITY_4: "50",
                    QUIC_MULTIPATH: kwargs["multipath"],
                    RMEM: (10240, 87380, 16777216),
                }
                if int(kwargs["multipath"]) == 0:
                    kwargs["protocol"] = "tcp"

                kwargs["postProcessing"] = getPostProcessingList(**kwargs)
                core.experiment(experienceLauncher, xpDict, **kwargs)

            core.experimentFor("multipath", [1], test, **kwargs)
            # core.experimentFor("multipath", [1], test, **kwargs)

        # core.experimentFor("xp", [HTTPS, QUIC], testsMultipath, **kwargs)
        core.experimentFor("xp", [QUIC], testsMultipath, **kwargs)

    core.experimentTopos(topos, "https_quic", protocol, tmpfs, testsXp)
    experienceLauncher.finish()


def generateExperimentalDesignRandomTopos(nbMptcpTopos=10, pathsPerTopo=2, bandwidth=(0.1, 100), rtt=(0, 50), queuingDelay=(0.0, 0.1), loss=(0.0, 2.5)):
    """ Assume only two paths per MPTCP topology, uniform distribution """
    mptcpTopos = []
    for nbTopo in range(nbMptcpTopos):
        mptcpTopo = {PATHS: [], NETEM: []}
        for nbPath in range(pathsPerTopo):
            bandwidthPath = "{0:.2f}".format(np.random.uniform(low=bandwidth[0], high=bandwidth[1]))
            rttPath = "{0:.0f}".format(np.random.uniform(low=rtt[0], high=rtt[1]))
            delayPath = "{0:.1f}".format(float(rttPath) / 2.0)
            lossPath = "{0:.2f}".format(np.random.uniform(low=loss[0], high=loss[1]))
            queuingDelayPath = "{0:.3f}".format(np.random.uniform(low=queuingDelay[0], high=queuingDelay[1]))
            # tcpTopos.append({PATHS: [{BANDWIDTH: bandwidthPath, DELAY: delayPath}], NETEM: [(0, 0, "loss " + str(lossPath) + "%")]})
            mptcpTopo[PATHS].append({BANDWIDTH: bandwidthPath, DELAY: delayPath, QUEUING_DELAY: queuingDelayPath})
            mptcpTopo[NETEM].append((nbPath, 0, "loss " + str(lossPath) + "%"))

        mptcpTopos.append(mptcpTopo)
        reversedMptcpTopoPaths = mptcpTopo[PATHS][::-1]
        reversedMptcpTopoNetem = []
        nbPath = 0
        for netem in mptcpTopo[NETEM][::-1]:
            reversedMptcpTopoNetem.append((nbPath, netem[1], netem[2]))
            nbPath += 1

        reversedMptcpTopo = {PATHS: reversedMptcpTopoPaths, NETEM: reversedMptcpTopoNetem}
        mptcpTopos.append(reversedMptcpTopo)

    return mptcpTopos


def launchTests(times=1):
    """ Notice that the loss must occur at time + 2 sec since the minitopo test waits for 2 seconds between launching the server and the client """
    #mptcpTopos = generateExperimentalDesignRandomTopos(nbMptcpTopos=200)
    #logging = open("topos_lowbdp_with_loss.log", 'w')
    #print(mptcpTopos, file=logging)
    #logging.close()
    mptcpTopos = [{'netem': [(0, 0, 'loss 0.00%'), (1, 0, 'loss 0.00%')], 'paths': [{'queuingDelay': '0', 'delay': '0.500000', 'bandwidth': '1'}, {'queuingDelay': '0', 'delay': '0.500000', 'bandwidth': '20'}]}]
    #mptcpTopos = [{'netem': [(0, 0, 'loss 0.00%')], 'paths': [{'queuingDelay': '0', 'delay': '1', 'bandwidth': '1'}]}]
    #mptcpTopos = [{'netem': [(0, 0, 'loss 0.00%')], 'paths': [{'queuingDelay': '0', 'delay': '50', 'bandwidth': '100'}]}]
    #mptcpTopos = [{'netem': [(0, 0, 'loss 2.49%')], 'paths': [{'queuingDelay': '0.1', 'delay': '50', 'bandwidth': '100'}]}]
    #mptcpTopos = [{'netem': [(0, 0, 'loss 0.00%')], 'paths': [{'queuingDelay': '0', 'delay': '1', 'bandwidth': '1'}]}]


    for i in range(times):
        quicTests(mptcpTopos)

launchTests(times=1)
