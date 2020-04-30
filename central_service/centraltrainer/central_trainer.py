import threading, queue
import time
import logging
import multiprocessing as mp

from utils.logger import config_logger  
from environment.environment import Environment
from .request_handler import RequestHandler


def environment(stopEnv, times=5):
    env = Environment(times)

    while not stopEnv.isSet():
        try:
            # run times
            env.run()
        except Exception as ex:
            print ("Environmnet exception " % ex)

def agent():
    pass

def coordinator():
    pass

class CentralTrainer():
    '''Few notes: CentralTrainer is responsible for its own threads!
        More will be explained later.
    '''
    def __init__(self):

        # Thread Variables
        self.__tqueue = queue.Queue(maxsize=1)

        # Process Variables
        self.__pqueue = queue.Queue()

        # Threads
        self.__rhandler = RequestHandler(threadID=10, threadName="RequestHandler-Thread", tqueue=self.__tqueue)
        self.__tList = [self.__rhandler]

        # Processes
        times=1
        self.__stopenv = mp.Event()
        self.__procenv = mp.Process(target=environment, args=(self.__stopenv, times))
        self.__procagent = mp.Process(target=agent, args=())
        self.__proccoordinator = mp.Process(target=coordinator, args=())

        self.__pList = [self.__procenv, self.__procagent, self.__proccoordinator]

        # Logger
        self.__logger = config_logger(name='central_trainer', filepath='./logs/ctrainer.log')

    @property
    def requesthandler(self):
        return self.__rhandler

    @property
    def threadsList(self):
        return self.__tList

    @property
    def environment(self):
        return self.__procenv

    @property
    def processesList(self):
        return self.__pList
    
    def run(self):
        '''Initiates threads and processes.'''
        self.requesthandler.start()
        self.environment.start()

        while True:
            request = self.getrequest()
            self.pinfo(request)

        # Shutdown everything
        self.close()

    def getrequest(self):
        while True:
            try:
                req = self.__tqueue.get(True, 0.05)
                return req
            except queue.Empty:
                # self.pinfo("Queue is empty")
                continue

    def putresponse(self, data):
        while True:
            try:
                self.__tqueue.put(data)
                break
            except Exception as ex:
                # self.pinfo("Cannot put item into Queue")
                self.pdebug(ex)

    def pdebug(self, msg):
        self.__logger.debug(msg)

    def pinfo(self, msg):
        self.__logger.info(msg)

    def close(self):
        # Send stop signals to request handler
        self.requesthandler.stophandler()
        self.__stopenv.set()

        for t in self.threadsList:
            t.join()


        for p in self.processesList:
            p.join()

        self.pdebug("CentralTrainer Shutting down gracefully...")