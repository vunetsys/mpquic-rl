# Simple queue operations
# get or put a request to queue
# blocking operation with a small timeout
import queue
from threading import Event
import multiprocessing as mp

def get_request(queue: queue.Queue, logger, end_of_run: mp.Event = None):
    # logger.info("Waiting for request...")
    while not end_of_run.is_set():
        try:
            req, evt = queue.get(timeout=0.05)
            return req, evt
        except Exception as ex:
            # logger.error(ex)
            continue
    return None, None

def put_response(response, queue: queue.Queue, logger):
    # logger.info("Putting response...")
    try:
        queue.put(response)
    except Exception as ex:
        logger.error(ex)