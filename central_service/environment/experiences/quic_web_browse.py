# from __future__ import print_function
import os
import numpy as np

from .core.generate_topo import PATHS, NETEM, BANDWIDTH, DELAY, QUEUING_DELAY

from .core.generate_xp import XP_TYPE, SCHEDULER_CLIENT, SCHEDULER_SERVER, CC, \
    CLIENT_PCAP, SERVER_PCAP, HTTPS_FILE, HTTPS_RANDOM_SIZE, QUIC_MULTIPATH, RMEM, \
    QUIC, HTTPS, WEB_BROWSE, JSON_FILE, PROJECT, PATH_SCHEDULER, BROWSER, SINGLE_FILE, \
    PRIORITY_HIGH, PRIORITY_LOW, DEPENDENCY_1, DEPENDENCY_2, HTTPS_RANDOM_SIZE2, \
    HTTPS_RANDOM_SIZE3, HTTPS_RANDOM_SIZE4, PRIORITY_3, PRIORITY_4, MULTIFILE, \
    HTTPS_RANDOM_SIZE5, PRIORITY_5

from .core.core import ExperienceLauncher, experiment, experimentFor, experimentTopos


REMOTE_SERVER_RUNNER_HOSTNAME = ["mininet@192.168.122.157"]
REMOTE_SERVER_RUNNER_PORT = ["22"]

DEFAULT_TOPOLOGY = [
        {'netem': [(0, 0, 'loss 1.56%'), (1, 0, 'loss 1.19%')], 
        'paths': [  
                    {'queuingDelay': '0.954', 'delay': '5.000000', 'bandwidth': '100'}, 
                    {'queuingDelay': '1.269', 'delay': '5.000000', 'bandwidth': '25'}
                ]
        }
    ]


def getPostProcessingList(**kwargs):
    toReturn = []
    # topoBasename = os.path.basename(kwargs["topoAbsPath"])
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


def quicTests(topos=DEFAULT_TOPOLOGY, graph="www.google.com_", protocol="mptcp", tmpfs="/mnt/tmpfs"): #work path
    experienceLauncher = ExperienceLauncher(REMOTE_SERVER_RUNNER_HOSTNAME, REMOTE_SERVER_RUNNER_PORT)

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
                    WEB_BROWSE: "1",     # single file transfer: 0  ;  web browse: 1
                    JSON_FILE: graph,   # specify websites to download
                    PROJECT: "quic-go",     # quic-go is the prioritized stream scheduling project, mp-quic is the original multipath-quic project
                    PATH_SCHEDULER:"MultiPath",   # quic-go param: MultiPath; SinglePath
                    BROWSER:"Firefox",
                    QUIC_MULTIPATH: kwargs["multipath"],
                    RMEM: (10240, 87380, 16777216),
                    # single file transfer parameters
                    SINGLE_FILE: "0", # default 0, means transfer two file simultaneously, if 1 only transfer the first file
                    HTTPS_RANDOM_SIZE: "20000",  # default to PRIORITY_HIGH
                    PRIORITY_HIGH: "255",  # quic-go priority seting: uint8 type from 1 to 255
                    DEPENDENCY_1: "0",  # The stream ID that this stream is dependent on
                    HTTPS_RANDOM_SIZE2: "32",
                    PRIORITY_LOW: "8",  # quic-go priority seting
                    DEPENDENCY_2: "0",  # can be 5  The stream ID that this stream is dependent on
                    MULTIFILE: "0", # default 0, cannot use bool because current minitopo cannot initiate bool value through "False"
                    HTTPS_RANDOM_SIZE3: "100",
                    PRIORITY_3: "150",
                    HTTPS_RANDOM_SIZE4: "15000",
                    PRIORITY_4: "50",
                    HTTPS_RANDOM_SIZE5: "500",
                    PRIORITY_5: "50",
                }
                if int(kwargs["multipath"]) == 0:
                    kwargs["protocol"] = "tcp"

                kwargs["postProcessing"] = getPostProcessingList(**kwargs)
                experiment(experienceLauncher, xpDict, **kwargs)

            experimentFor("multipath", [1], test, **kwargs)
            # core.experimentFor("multipath", [1], test, **kwargs)

        # core.experimentFor("xp", [HTTPS, QUIC], testsMultipath, **kwargs)
        experimentFor("xp", [QUIC], testsMultipath, **kwargs)

    experimentTopos(topos, "https_quic", protocol, tmpfs, testsXp)
    experienceLauncher.finish()


def generateExperimentalDesignRandomTopos(nbMptcpTopos=10, pathsPerTopo=2, bandwidth=(0.1, 100), rtt=(0, 50), queuingDelay=(0.0, 0.1), loss=(0.0, 2.5)):
    """ Assume only two paths per MPTCP topology, uniform distribution """
    mptcpTopos = []
    for _ in range(nbMptcpTopos):
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


def launchTests(topology, graph):
    # topology = [
    #     {'netem': [(0, 0, 'loss 1.56%'), (1, 0, 'loss 1.19%')], 
    #     'paths': [
    #         {'bandwidth': '51', 'delay': '10.5', 'queuingDelay': '0.048'}, 
    #         {'bandwidth': '45', 'delay': '13.3', 'queuingDelay': '0.063'}
    #     ]}
    # ]
    quicTests(topology, graph)