import threading, queue
import time
import zmq
import logging
import sys
import json


from utils.logger import config_logger

class RequestHandler(threading.Thread):
    ''' RequestHandler will receive requests from MPQUIC
        Pass on the requests to the agent
        Obtain a response (scheduling-related) and send it back
    '''
    def __init__(self, threadID: int, threadName: str, tqueue: queue.Queue, host:str="localhost", port:str="5555"):
        threading.Thread.__init__(self)

        # Threading variables
        self._threadID = threadID
        self._threadName = threadName
        self.__tqueue = tqueue
        self.__stoprequest = threading.Event()

        self.__logger = config_logger(name='request_handler', filepath='./logs/rhandler.log')

        # ZMQ context
        self.__host = host
        self.__port = port
        
        self.__context = zmq.Context()
        self._server = self.__context.socket(zmq.REP)
        self._server.connect("tcp://%s:%s" % (self.__host, self.__port))

        self.__poller = zmq.Poller()
        self.__poller.register(self._server, zmq.POLLIN)

    def run(self):
        self.pinfo("Run Request Handler")
        while not self.__stoprequest.isSet():
            try:
                # Poll for a reply => time is ms
                if (self.__poller.poll(timeout=50)):
                    # Receive request from middleware
                    try:
                        data = self._server.recv_multipart(zmq.NOBLOCK)
                    except Exception as ex:
                        self.pdebug(ex)

                    json_data = json.loads(data[1])
                    self.pinfo(json_data)
                    
                    # put request on the Queue (blocking operation)
                    ev1 = threading.Event()
                    self.putrequest(json_data, ev1)
                    ev1.wait() # blocks until `consumer` (i.e. agent) receives request
                    
                    response, ev2 = self.getresponse()
                    ev2.set() # lets `producer` (i.e. agent) know the response has been received

                    self.pinfo(response)
                    self.pinfo("Got my response from agent -- forwarding to quic")
                    
                    # give back response
                    self._server.send_multipart(response)
            except Exception as ex:
                self.pdebug(ex)
        self.close()

    def getresponse(self):
        while not self.__stoprequest.isSet():
            try:
                resp, flag = self.__tqueue.get(True, 0.05)
                return resp, flag
            except queue.Empty:
                self.pinfo("Queue is empty")
                continue

    def putrequest(self, data, flag):
        while not self.__stoprequest.isSet():
            try:
                self.__tqueue.put((data, flag), True, 0.05)
                break
            except Exception as ex:
                self.pinfo("Cannot put item into Queue")
                self.pdebug(ex)

    def pdebug(self, msg):
        self.__logger.debug(msg)

    def pinfo(self, msg):
        self.__logger.info(msg)

    def stophandler(self):
        self.__stoprequest.set()

    def close(self):
        self._server.close()
        self.__context.term()
        self.pinfo("RequestHandler closing gracefully...")



if __name__ == "__main__":
    tqueue = queue.Queue()

    rh = RequestHandler(1, 'test-requesthandler', tqueue=tqueue)
    rh.start()
    rh.join()