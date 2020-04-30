import numpy as np
import multiprocessing as mp
import subprocess
import time

# from .experiences.quic_mptcp_https_tests_expdes_wsp_highbdp_loss_quic_marios import launchTests
# from .experiences.quic_dualfile_offline import launchTests 
from .experiences.quic_web_browse import launchTests


MIDDLEWARE_SOURCE_REMOTE_PATH = "~/go/src/github.com/mkanakis/zserver"
MIDDLEWARE_BIN_REMOTE_PATH = "./go/bin/reply"


class Environment:
    def __init__(self, logger, times=5, remoteHostname="mininet@192.168.122.15", remotePort="22"):
        self._totalRuns = 0
        self._logger = logger
        self._times = times

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
        self._totalRuns += 1
        message = "Run Number: {}" 
        self._logger.info(message.format(self._totalRuns))
        # actual test launcher
        launchTests(self._times)

    def close(self):
        self.stop_middleware()
        self._logger.info("Environment closing gracefully...")