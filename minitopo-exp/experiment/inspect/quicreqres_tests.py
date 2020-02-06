#! /usr/bin/python

from __future__ import print_function

# Doing * imports is bad :'(
from experiences.core.generate_topo import *
from experiences.core.generate_xp import *

import experiences.core.core as core
import os

REMOTE_SERVER_RUNNER_HOSTNAME = ["mininet@localhost"]
REMOTE_SERVER_RUNNER_PORT = ["8022"]


def getPostProcessingList(**kwargs):
    toReturn = []
    topoBasename = os.path.basename(kwargs["topoAbsPath"])
    toReturn.append(("client.pcap",
                     "_".join([str(x) for x in [kwargs["testDirectory"], kwargs["protocol"], kwargs["multipath"],
                                                topoBasename, "client.pcap"]])))
    toReturn.append(("server.pcap",
                     "_".join([str(x) for x in [kwargs["testDirectory"], kwargs["protocol"], kwargs["multipath"],
                                                topoBasename, "server.pcap"]])))
    toReturn.append(("command.log", "command.log"))
    toReturn.append(("ping.log", "ping.log"))
    toReturn.append(("quic_client.log", "quic_client.log"))
    toReturn.append(("quic_server.log", "quic_server.log"))
    toReturn.append(("netstat_client_before", "netstat_client_before"))
    toReturn.append(("netstat_server_before", "netstat_server_before"))
    toReturn.append(("netstat_client_after", "netstat_client_after"))
    toReturn.append(("netstat_server_after", "netstat_server_after"))

    return toReturn


def quicSiriTests(topos, protocol="mptcp", tmpfs="/mnt/tmpfs"):
    experienceLauncher = core.ExperienceLauncher(REMOTE_SERVER_RUNNER_HOSTNAME, REMOTE_SERVER_RUNNER_PORT)

    def testsMultipath(**kwargs):
        def test(**kwargs):
            xpDict = {
                XP_TYPE: QUICREQRES,
                SCHEDULER_CLIENT: "default",
                SCHEDULER_SERVER: "default",
                CC: "olia" if kwargs["multipath"] == 1 else "cubic",
                CLIENT_PCAP: "yes",
                SERVER_PCAP: "yes",
                QUIC_MULTIPATH: kwargs["multipath"],
                QUICREQRES_RUN_TIME: 30,
                RMEM: (10240, 87380, 16777216),
            }
            if int(kwargs["multipath"]) == 0:
                kwargs["protocol"] = "tcp"

            kwargs["postProcessing"] = getPostProcessingList(**kwargs)
            core.experiment(experienceLauncher, xpDict, **kwargs)

        core.experimentFor("multipath", [0, 1], test, **kwargs)
        # core.experimentFor("multipath", [1], test, **kwargs)

    core.experimentTopos(topos, "siri_quicreqres", protocol, tmpfs, testsMultipath)
    experienceLauncher.finish()


def launchTests(times=5):
    """ Notice that the loss must occur at time + 2 sec since the minitopo test waits for 2 seconds between launching the server and the client """
    topos = [
        {PATHS: [{DELAY: 7.5, BANDWIDTH: 10}, {DELAY: 12.5, BANDWIDTH: 10}], NETEM: [(0, 0, "loss 0%"), (1, 0, "loss 0%")]},
        {PATHS: [{DELAY: 7.5, BANDWIDTH: 10}, {DELAY: 12.5, BANDWIDTH: 10}], NETEM: [(0, 0, "loss 0%"), (1, 0, "loss 0%"), (0, 7, "loss 5%")]},
        {PATHS: [{DELAY: 7.5, BANDWIDTH: 10}, {DELAY: 12.5, BANDWIDTH: 10}], NETEM: [(0, 0, "loss 0%"), (1, 0, "loss 0%"), (0, 7, "loss 25%")]},
        {PATHS: [{DELAY: 7.5, BANDWIDTH: 10}, {DELAY: 12.5, BANDWIDTH: 10}], NETEM: [(0, 0, "loss 0%"), (1, 0, "loss 0%"), (0, 7, "loss 50%")]},
        {PATHS: [{DELAY: 7.5, BANDWIDTH: 10}, {DELAY: 12.5, BANDWIDTH: 10}], NETEM: [(0, 0, "loss 0%"), (1, 0, "loss 0%"), (0, 7, "loss 100%")]},
    ]

    for i in range(times):
        quicSiriTests(topos)

launchTests(times=5)
