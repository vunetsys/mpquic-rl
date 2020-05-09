import numpy as np
import threading
import multiprocessing as mp
import subprocess
import time

# from .experiences.quic_mptcp_https_tests_expdes_wsp_highbdp_loss_quic_marios import launchTests
# from .experiences.quic_dualfile_offline import launchTests 
from .experiences.quic_web_browse import launchTests
from utils.logger import config_logger


MIDDLEWARE_SOURCE_REMOTE_PATH = "~/go/src/github.com/mkanakis/zserver"
MIDDLEWARE_BIN_REMOTE_PATH = "./go/bin/reply"

import json
import os
from threading import Lock


class Session:
    '''
        This class loads and parses one by one all configurations
        for our environment!
        It is utilized by both agent and environment
    '''
    def __init__(self, topologies='./environment/topos.json', dgraphs='./environment/dependency_graphs'):
        self._lock = Lock()
        
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
        self._lock.acquire()
        self._topoIndex = (self._topoIndex + 1) % self._len_topo
        self._lock.release()

    def nextGraph(self):
        self._lock.acquire()
        self._graphIndex = (self._topoIndex + 1) % self._len_graph
        self._lock.release()

    def getCurrentTopo(self):
        self._lock.acquire()
        topo = self._topologies[self._topoIndex]
        self._lock.release()
        return topo

    def getCurrentGraph(self):
        self._lock.acquire()
        graph = self._graphs[self._graphIndex]
        self._lock.release()
        return graph

    def getCurrentBandwidth(self):
        topo = self.getCurrentTopo()
        return topo['paths'][0]['bandwidth'], topo['paths'][1]['bandwidth']


class Environment(threading.Thread):
    def __init__(self, threadID: int, threadName: str, end_of_run: threading.Event, remoteHostname="mininet@192.168.122.15", remotePort="22"):
        threading.Thread.__init__(self)

        self._threadID = threadID
        self._threadName = threadName
        self._stop_env = threading.Event()
        self.end_of_run = end_of_run

        self._logger = config_logger('environment', filepath='./logs/environment.log')

        self._totalRuns = 0

        # Init session
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
        # Lets measure env runs in time
        while not self._stop_env.is_set():

            # Only the agent can unblock this loop, after a training-batch has been completed
            while not self.end_of_run.is_set():
                try:
                    now = time.time()
                    #------------------------
                    self._totalRuns += 1
                    message = "Run Number: {}" 
                    self._logger.info(message.format(self._totalRuns))
                    launchTests()
                    #------------------------
                    end = time.time()

                    diff = int (end - now)
                    self._logger.debug("Time to execute one run: {}s".format(diff))


                    # update topology
                    # update configuration
                    self.session.nextTopo()
                    self.session.nextGraph()

                    self.end_of_run.set() # set the end of run so our agent knows
                    # env.spawn_middleware() # restart middleware 
                except Exception as ex:
                    self._logger.error(ex)
                    break
            time.sleep(0.1)

        # Closing environment, inform others that this is the end 
        # By raising the stop_env flag
        if not self._stop_env.is_set():
            self.stopenv()
        self.close()

    def stopenv(self):
        self._stop_env.set()

    def close(self):
        self.stop_middleware()
        self._logger.info("Environment closing gracefully...")