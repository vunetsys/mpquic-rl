# Simple queue operations
# get or put a request to queue
# blocking operation with a small timeout
import queue
import multiprocessing as mp

def get_request(queue: queue.Queue, logger, end_of_run: mp.Event = None):
    logger.info("Waiting for request...")
    if end_of_run is not None:
        while not end_of_run.is_set():
            try:
                req = queue.get(timeout=0.05)
                return req
            except Exception as ex:
                # logger.error(ex)
                continue
        return None
    else:
        try:
            req = queue.get()
            return req
        except Exception as ex:
            logger.error(ex)

def put_response(response, queue: queue.Queue, logger, end_of_run: mp.Event = None):
    logger.info("Putting response...")
    if end_of_run is not None:
        while not end_of_run.is_set():
            try:
                queue.put(response, timeout=0.05)
                return response
            except Exception as ex:
                # logger.error(ex)
                continue
        return None
    else:
        try:
            queue.put(response)
        except Exception as ex:
            logger.error(ex)