import threading, queue
import time
import zmq
import logging
import sys
import json

sys.path.append("")


from utils.logger import config_logger
# from logger import config_logger

class BasicThread(threading.Thread):
    '''
        This is BasicThread configuration that will be implemented
        in middleware threads (request handler, collector)
    '''
    def __init__(self, threadID: int, threadName: str, queue: queue.Queue):
        threading.Thread.__init__(self)

        # Threading variables
        self._threadID = threadID
        self._threadName = threadName
        self._queue = queue
        self._stoprequest = threading.Event()

        self.__logger = config_logger(name=self._threadName, filepath='./logs/{}.log'.format(self._threadName))

    def run(self):
        self.run()

    def getresponse(self):
        while not self._stoprequest.isSet():
            try:
                resp = self._queue.get(True, 0.05)
                return resp
            except queue.Empty:
                self.pinfo("Queue is empty")
                continue

    def putrequest(self, data):
        while not self._stoprequest.isSet():
            try:
                self._queue.put(data, True, 0.05)
                break
            except Exception as ex:
                self.pinfo("Cannot put item into Queue")
                self.pdebug(ex)

    def pdebug(self, msg):
        self.__logger.debug(msg)

    def pinfo(self, msg):
        self.__logger.info(msg)

    def stophandler(self):
        self._stoprequest.set()

    def close(self):
        self.close()

