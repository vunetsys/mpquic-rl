import numpy as np
import threading
import multiprocessing as mp
import subprocess
import time
import json
import os
import random

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
    def __init__(self, topologies='./environment/topos.json', dgraphs='./environment/graphs.json'):
        self._index = 0

        self._topologies, self._len_topo = self.loadTopologies(topologies)
        self._graphs, self._len_graph  = self.loadDependencyGraphs(dgraphs)

        self._pairs = self.generatePairs()


    def generatePairs(self):
        tuple_list = []
        for i in range(self._len_topo):
            for j in range(self._len_graph):
                tuple_list.append((i, j))

        return random.sample(tuple_list, len(tuple_list))

    def loadTopologies(self, file):
        topos = []
        with open(file, 'r') as fp:
            topos = json.load(fp)

        return topos, len(topos)

    def loadDependencyGraphs(self, file):
        graphs = []
        with open(file, 'r') as fp:
            graphs = json.load(fp)

        output = [elem['file'] for elem in graphs]
        return output, len(output)

    # nextTopo and nextGraph allow only one thread at both methods at a time!
    def nextRun(self):
        self._index += 1

        if self._index >= len(self._pairs):
            return -1
        return self._index 

    def getCurrentTopo(self):
        topo = self._topologies[self._pairs[self._index][0]]
        return topo

    def getCurrentGraph(self):
        graph = self._graphs[self._pairs[self._index][1]]
        return graph

    def getCurrentBandwidth(self):
        topo = self.getCurrentTopo()
        return int(topo['paths'][0]['bandwidth']), int(topo['paths'][1]['bandwidth'])


class Environment:
    def __init__(self, bdw_paths, logger, remoteHostname="mininet@192.168.122.15", remotePort="22"):
        self._totalRuns = 0
        self._logger = logger

        # Session object
        self.session = Session()
        self.curr_topo = Session().getCurrentTopo()
        self.curr_graph = Session().getCurrentGraph()
        self.bdw_paths = bdw_paths

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

    def getNetemToTuple(self, topo):
        '''in json -> tuple (0 0 loss 1.69%) is stored as [0, 0, loss 1.69%]
            revert it back to tuple, otherwise error is produced
        '''
        topo[0]['netem'][0] = (topo[0]['netem'][0][0], topo[0]['netem'][0][1], topo[0]['netem'][0][2])
        topo[0]['netem'][1] = (topo[0]['netem'][1][0], topo[0]['netem'][1][1], topo[0]['netem'][1][2])
        return topo

    def updateEnvironment(self):
        ''' One step update 
            First load current values, then move to next!
        '''
        topo = [self.session.getCurrentTopo()]
        self.curr_topo = self.getNetemToTuple(topo)
        self.curr_graph = self.session.getCurrentGraph()

        bdw_path1, bdw_path2 = self.session.getCurrentBandwidth()
        self.bdw_paths[0] = bdw_path1
        self.bdw_paths[1] = bdw_path2

        return self.session.nextRun()
        
    def run(self):
        self._totalRuns += 1
        message = "Run Number: {}" 
        self._logger.info(message.format(self._totalRuns))

        launchTests(self.curr_topo, self.curr_graph)

    def close(self):
        self.stop_middleware()
        self._logger.info("Environment closing gracefully...")