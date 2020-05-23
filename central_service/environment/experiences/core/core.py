from __future__ import print_function

from .generate_topo import generateTopoFile, PATHS, DELAY, QUEUE_SIZE, QUEUING_DELAY, BANDWIDTH, LOSS, NETEM
from .generate_xp import generateXpFile
import queue

import os
import subprocess
import time
import threading

""" Let 2 hours to complete the experiment """
# This should be sufficient for the worst case topology (~0.10 Mbps to download 20 MB on single-path)
# THREAD_TIMEOUT = 7200
THREAD_TIMEOUT = 45


""" Some useful functions """


def check_directory_exists(directory):
    """ Check if the directory exists, and create it if needed
        If directory is a file, raise an Exception
    """
    if os.path.exists(directory):
        if not os.path.isdir(directory):
            raise Exception(directory + " is a file")
    else:
        os.makedirs(directory)


def topoToFilename(topo):
    i = 0
    toReturn = ""
    for path in topo.get(PATHS, []):
        if len(toReturn) > 0:
            toReturn += "_"
        toReturn += str(i) + "_"
        if DELAY in path:
            toReturn += "d" + str(path[DELAY])
        if QUEUE_SIZE in path:
            toReturn += "q" + str(path[QUEUE_SIZE])
        elif QUEUING_DELAY in path:
            toReturn += "qs" + str(path[QUEUING_DELAY])
        if BANDWIDTH in path:
            toReturn += "b" + str(path[BANDWIDTH])
        if LOSS in path:
            toReturn += "l" + str(path[LOSS])
        i += 1
    for netem in topo.get(NETEM, []):
        toReturn += "_nt_" + str(netem[0]) + "_" + str(netem[1]) + "_" + str(netem[2]).replace(" ", "_")

    return toReturn


class MinitopoCommand(object):
    """ The actual Minitopo command """
    def __init__(self, num, remoteHostname, remotePort, cmd, cwd, testOkList):
        self.num = num
        self.remoteHostname = remoteHostname
        self.remotePort = remotePort
        self.cmd = cmd
        self.cwd = cwd
        self.testOkList = testOkList
        self.process = None

    def run(self, timeout):
        global testOkList

        def target():
            try:
                self.process = subprocess.Popen(self.cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                minitopoOut = open(os.path.join(self.cwd, "minitopo.out"), "wb")
                minitopoErr = open(os.path.join(self.cwd, "minitopo.err"), "wb")
                minitopoOut.writelines(self.process.stdout.readlines())
                minitopoErr.writelines(self.process.stderr.readlines())
                minitopoOut.close()
                minitopoErr.close()
                self.process.communicate()
            except Exception as e:
                print(str(e) + ": continue")

        self.testOkList[self.num] = True

        thread = threading.Thread(target=target)
        thread.start()

        thread.join(timeout)
        if thread.is_alive():
            # print("Experience terminated!")
            print("Experience failed; take a look on the machine")
            time.sleep(66666666666)
            # time.sleep(600)
            self.testOkList[self.num] = False
            self.process.kill()
            devnull = open(os.devnull, "w")
            self.process = subprocess.Popen('ssh -p ' + self.remotePort + ' ' + self.remoteHostname + ' "sudo pkill -f mpPerf.py"',
                                            shell=True, stdout=devnull, stderr=devnull)
            time.sleep(1)
            self.process = subprocess.Popen('ssh -p ' + self.remotePort + ' ' + self.remoteHostname + ' "sudo reboot"',
                                            shell=True, stdout=devnull, stderr=devnull)
            time.sleep(15)
            self.process = subprocess.Popen('ssh -p ' + self.remotePort + ' ' + self.remoteHostname + ' "sudo mn -c"',
                                            shell=True, stdout=devnull, stderr=devnull)
            time.sleep(5)

        # Be sure
        try:
            self.process.kill()
        except OSError:
            # Avoid exception if we just want to be sure
            pass


class ExperienceLauncher(object):
    """ Keep track of all needed to launch experiences """
    def __init__(self, remoteHostnames, remotePorts):
        self.remoteHostnames = remoteHostnames
        self.remotePorts = remotePorts

        if not len(self.remoteHostnames) == len(self.remotePorts):
            raise Exception("remoteHostnames and remotePorts with different lengths")

        if len(self.remoteHostnames) <= 0:
            raise Exception("No remote server specified")

        self.workQueue = queue.Queue(len(self.remoteHostnames))
        self.finished = False
        self.testOkList = [True] * len(self.remoteHostnames)
        self.threads = []

        for threadId in range(len(self.remoteHostnames)):
            thread = threading.Thread(target=self.workerLoop, args=(threadId,))
            thread.start()
            self.threads.append(thread)

    def putOnRemote(self, num, filename, path):
        cmd = "scp -P " + self.remotePorts[num] + " " + filename + " " + self.remoteHostnames[num] + ":" + path
        if subprocess.call(cmd.split()) != 0:
            raise Exception("File " + filename + " could not be put on remote server at path " + path)

    def pullHereFromRemote(self, num, filename, path, newFilename):
        cmd = "scp -P " + self.remotePorts[num] + " " + self.remoteHostnames[num] + ":" + path + "/" + filename + " " + newFilename
        if subprocess.call(cmd.split()) != 0:
            raise Exception("File " + filename + " could not be pull from remote server at path " + path)

    def changeMptcpEnabled(self, num, value):
        cmd = ["ssh", "-p", self.remotePorts[num], self.remoteHostnames[num], "sudo sysctl net.mptcp.mptcp_enabled=" + str(value)]
        if subprocess.call(cmd) != 0:
            raise Exception("Cannot change value of mptcp_enabled at " + str(value))

    def changeOpenBup(self, num, value):
        """ Also disable the oracle if openBup is enabled """
        cmd = ["ssh", "-p", self.remotePorts[num], self.remoteHostnames[num],
               "echo " + str(value).split('-')[0] + " | sudo tee /sys/module/mptcp_fullmesh/parameters/open_bup"]
        if subprocess.call(cmd) != 0:
            raise Exception("Cannot change value of open_bup at " + str(value))

        if value == "0" or value == "0-250":
            sloss_threshold, sretrans_threshold, rto_ms_threshold, idle_periods_threshold, timer_period_ms = "250", "500", "1500", "0", "500"
        elif value == "0-400":
            sloss_threshold, sretrans_threshold, rto_ms_threshold, idle_periods_threshold, timer_period_ms = "400", "500", "1500", "0", "500"
        elif value == "0-100":
            sloss_threshold, sretrans_threshold, rto_ms_threshold, idle_periods_threshold, timer_period_ms = "100", "500", "1500", "0", "500"
        elif value == "0-t1":
            sloss_threshold, sretrans_threshold, rto_ms_threshold, idle_periods_threshold, timer_period_ms = "250", "500", "1500", "0", "1"
        elif value == "0-t10":
            sloss_threshold, sretrans_threshold, rto_ms_threshold, idle_periods_threshold, timer_period_ms = "250", "500", "1500", "0", "10"
        elif value == "0-t100":
            sloss_threshold, sretrans_threshold, rto_ms_threshold, idle_periods_threshold, timer_period_ms = "250", "500", "1500", "0", "100"
        elif value == "0-t500":
            sloss_threshold, sretrans_threshold, rto_ms_threshold, idle_periods_threshold, timer_period_ms = "250", "500", "1500", "0", "500"
        elif value == "0-t1000":
            sloss_threshold, sretrans_threshold, rto_ms_threshold, idle_periods_threshold, timer_period_ms = "250", "500", "1500", "0", "1000"
        elif value == "0-T750":
            sloss_threshold, sretrans_threshold, rto_ms_threshold, idle_periods_threshold, timer_period_ms = "250", "500", "750", "0", "100"
        elif value == "0-t100-T500":
            sloss_threshold, sretrans_threshold, rto_ms_threshold, idle_periods_threshold, timer_period_ms = "250", "500", "500", "0", "100"
        else:
            sloss_threshold, sretrans_threshold, rto_ms_threshold, idle_periods_threshold, timer_period_ms = "0", "0", "0", "0", "500"

        cmd = ["ssh", "-p", self.remotePorts[num], self.remoteHostnames[num],
               "echo " + sloss_threshold + " | sudo tee /sys/module/mptcp_oracle/parameters/sloss_threshold"]
        if subprocess.call(cmd) != 0:
            raise Exception("Cannot change value of sloss_threshold at " + sloss_threshold)

        cmd = ["ssh", "-p", self.remotePorts[num], self.remoteHostnames[num],
               "echo " + sretrans_threshold + " | sudo tee /sys/module/mptcp_oracle/parameters/sretrans_threshold"]
        if subprocess.call(cmd) != 0:
            raise Exception("Cannot change value of sretrans_threshold at " + sretrans_threshold)

        cmd = ["ssh", "-p", self.remotePorts[num], self.remoteHostnames[num],
               "echo " + rto_ms_threshold + " | sudo tee /sys/module/mptcp_oracle/parameters/rto_ms_threshold"]
        if subprocess.call(cmd) != 0:
            raise Exception("Cannot change value of rto_ms_threshold at " + rto_ms_threshold)

        cmd = ["ssh", "-p", self.remotePorts[num], self.remoteHostnames[num],
               "echo " + idle_periods_threshold + " | sudo tee /sys/module/mptcp_oracle/parameters/idle_periods_threshold"]
        if subprocess.call(cmd) != 0:
            raise Exception("Cannot change value of idle_periods_threshold at " + idle_periods_threshold)

        cmd = ["ssh", "-p", self.remotePorts[num], self.remoteHostnames[num],
               "echo " + timer_period_ms + " | sudo tee /sys/module/mptcp_oracle/parameters/timer_period_ms"]
        if subprocess.call(cmd) != 0:
            raise Exception("Cannot change value of timer_period_ms at " + timer_period_ms)

    def postProcessing(self, num, **kwargs):
        """ Can have two or three elements in tuple, remotePath can be ignored (replaced by kwargs["tmpfs"]) """
        for postProcess in kwargs["postProcessing"]:
            if len(postProcess) == 2:
                remoteFilename, localFilename = postProcess
                remotePath = kwargs["tmpfs"]
            elif len(postProcess) == 3:
                remoteFilename, remotePath, localFilename = postProcess
            else:
                raise Exception("Invalid number of elements in postProcessing: " + str(postProcess))

            self.pullHereFromRemote(num, remoteFilename, remotePath, os.path.join(kwargs["workingDir"], localFilename))

    def cleanMininet(self, num):
        cmd = ["ssh", "-p", self.remotePorts[num], self.remoteHostnames[num], "timeout 20 sudo mn -c"]
        devnull = open(os.devnull, 'w')
        if subprocess.call(cmd, stdout=devnull, stderr=devnull) != 0:
            # raise Exception("Cannot clean mininet for thread " + str(num))
            subprocess.Popen('ssh -p ' + self.remotePorts[num] + ' ' + self.remoteHostnames[num] + ' "sudo mn -c"',
                             shell=True, stdout=devnull, stderr=devnull)
            time.sleep(30)

        devnull.close()
        time.sleep(1)

    def launchXp(self, num, **kwargs):
        if kwargs["protocol"] == "tcp":
            self.changeMptcpEnabled(num, 0)
        elif kwargs["protocol"] == "mptcp":
            self.changeMptcpEnabled(num, 1)
        else:
            protocol = kwargs["protocol"]
            raise Exception("Unknown protocol " + protocol)

        if "openBup" in kwargs:
            self.changeOpenBup(num, kwargs["openBup"])

        self.cleanMininet(num)
        cmd = 'ssh -p ' + self.remotePorts[num] + ' ' + self.remoteHostnames[num] + \
              ' "cd ' + kwargs["tmpfs"] + '; sudo ~/git/minitopo/src/mpPerf.py -x ' + os.path.basename(kwargs["xpAbsPath"]) + ' -t ' + \
              os.path.basename(kwargs["topoAbsPath"]) + '"'
        MinitopoCommand(num, self.remoteHostnames[num], self.remotePorts[num], cmd, kwargs["workingDir"], self.testOkList).run(timeout=THREAD_TIMEOUT)

    def threadLaunchXp(self, num, **kwargs):
        global testOkList

        self.putOnRemote(num, kwargs["topoAbsPath"], kwargs["tmpfs"])
        self.putOnRemote(num, kwargs["xpAbsPath"], kwargs["tmpfs"])

        printStr = "Thread " + str(num)
        for key in kwargs:
            if key != "postProcessing" and key != "topo":
                printStr += " " + key + " " + str(kwargs[key])

        print(printStr)

        self.launchXp(num, **kwargs)

        if self.testOkList[num]:
            try:
                self.postProcessing(num, **kwargs)
            except Exception as e:
                print(str(e) + ": continue")

    def workerLoop(self, num):
        while not self.finished or not self.workQueue.empty():
            workData = self.workQueue.get()
            self.threadLaunchXp(num, **workData)
            self.workQueue.task_done()

    def addWork(self, **kwargs):
        self.workQueue.put(kwargs)

    def finish(self):
        """ Function to call to clean properly the experiences """
        if not self.finished:
            self.finished = True
            for thread in self.threads:
                thread.join()

    def __del__(self):
        self.finish()


def experiment(experienceLauncher, xpDict, **kwargs):
    xpFilename = kwargs["xpName"] + "Test"
    generateXpFile(xpFilename, xpDict)
    xpAbsPath = os.path.abspath(xpFilename)
    kwargs["workingDir"] = os.getcwd()
    kwargs["xpAbsPath"] = xpAbsPath
    experienceLauncher.addWork(**kwargs)


def experimentFor(keyword, elems, xpFnct, **kwargs):
    for elem in elems:
        if "skipIf" in kwargs and kwargs["skipIf"](elem, **kwargs):
            continue

        if isinstance(elem, tuple):
            strElem = "_".join(elem)
        else:
            strElem = str(elem)
        check_directory_exists(strElem)
        os.chdir(strElem)

        kwargs[keyword] = elem
        xpFnct(**kwargs)

        os.chdir("..")


def experimentTopos(topos, xpName, protocol, tmpfs, xpFnct, **kwargs):
    testDirectory = xpName + "_" + time.strftime("%Y%m%d_%H%M%S") + "_" + protocol
    check_directory_exists(testDirectory)
    os.chdir(testDirectory)

    for topo in topos:
        topoFilename = topoToFilename(topo)
        check_directory_exists(topoFilename)
        os.chdir(topoFilename)
        generateTopoFile(topoFilename, topo)
        topoAbsPath = os.path.abspath(topoFilename)

        xpFnct(xpName=xpName, testDirectory=testDirectory, topoAbsPath=topoAbsPath, protocol=protocol, topo=topo, tmpfs=tmpfs, **kwargs)

        os.chdir("..")

    os.chdir("..")


if __name__ == '__main__':
    topoDict = {
        PATHS: [{DELAY: 35, QUEUE_SIZE: 15}, {BANDWIDTH: 20}, {DELAY: 10, BANDWIDTH: 1}],
        NETEM: [(1, 3, "loss 1%")]
    }

    def test(**kwargs):
        for key in kwargs:
            print(key, kwargs[key])

    def cc(**kwargs):
        experimentFor("cc", ["olia"], test, **kwargs)

    def sched(**kwargs):
        experimentFor("sched", ["default", "preventive"], cc, **kwargs)

    # experimentTopos([topoDict], "test", "mptcp", sched, love=True)
