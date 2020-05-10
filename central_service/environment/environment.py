import numpy as np
import threading
import multiprocessing as mp
import subprocess
import time
import json
import os

# from .experiences.quic_mptcp_https_tests_expdes_wsp_highbdp_loss_quic_marios import launchTests
# from .experiences.quic_dualfile_offline import launchTests 
from .experiences.quic_web_browse import launchTests
from utils.logger import config_logger


MIDDLEWARE_SOURCE_REMOTE_PATH = "~/go/src/github.com/mkanakis/zserver"
MIDDLEWARE_BIN_REMOTE_PATH = "./go/bin/reply"

class Session:
    '''
        This class loads and parses one by one all configurations
        for our environment!
        It is utilized by both agent and environment
    '''
    def __init__(self, topologies='./environment/topos.json', dgraphs='./environment/dependency_graphs'):
        self._topoIndex = 0
        self._graphIndex = 0

        self._topologies, self._len_topo = self.loadTopologies(topologies)
        self._graphs, self._len_graph  = self.loadDependencyGraphs(dgraphs)


    def loadTopologies(self, file):
        topos = []
        with open(file, 'r') as fp:
            topos = json.load(fp)

        return topos, len(topos)

    def loadDependencyGraphs(self, file):
        output = [dI for dI in os.listdir(file) if os.path.isdir(os.path.join(file,dI))]
        return output, len(output)

    # nextTopo and nextGraph allow only one thread at both methods at a time!
    def nextTopo(self):
        self._topoIndex = (self._topoIndex + 1) % self._len_topo

    def nextGraph(self):
        self._graphIndex = (self._graphIndex + 1) % self._len_graph

    def getCurrentTopo(self):
        topo = self._topologies[self._topoIndex]
        return topo

    def getCurrentGraph(self):
        graph = self._graphs[self._graphIndex]
        return graph

    def getCurrentBandwidth(self):
        topo = self.getCurrentTopo()
        return topo['paths'][0]['bandwidth'], topo['paths'][1]['bandwidth']


class Environment:
    def __init__(self, logger, remoteHostname="mininet@192.168.122.15", remotePort="22"):
        self._totalRuns = 0
        self._logger = logger

        # Session object
        self.session = Session()

        # Spawn Middleware
        self._remoteHostname = remoteHostname
        self._remotePort = remotePort
        self.spawn_middleware()

    def spawn_middleware(self):
        # Beforing spawning a middleware,
        # Ensure that previous ones are killed!
        self.stop_middleware()
        time.sleep(0.5)
        ssh_cmd = ["ssh", "-p", self._remotePort, self._remoteHostname, MIDDLEWARE_BIN_REMOTE_PATH]
        subprocess.Popen(ssh_cmd, 
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, 
                        shell=False)

    def stop_middleware(self):
        kill_cmd = "killall " + MIDDLEWARE_BIN_REMOTE_PATH
        ssh_cmd = ["ssh", "-p", self._remotePort, self._remoteHostname, kill_cmd]
        subprocess.Popen(ssh_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=False)

    def run(self):
        topo = [self.session.getCurrentTopo()]
        self._logger.info(topo)
        topo[0]['netem'][0] = (topo[0]['netem'][0][0], topo[0]['netem'][0][1], topo[0]['netem'][0][2])
        topo[0]['netem'][1] = (topo[0]['netem'][1][0], topo[0]['netem'][1][1], topo[0]['netem'][1][2])


        self._logger.info(topo)

        graph = self.session.getCurrentGraph()

        self._totalRuns += 1
        message = "Run Number: {}" 
        self._logger.info(message.format(self._totalRuns))

        launchTests(topo, graph)

        # update topology
        # update configuration
        self.session.nextTopo()
        self.session.nextGraph()

    def close(self):
        self.stop_middleware()
        self._logger.info("Environment closing gracefully...")