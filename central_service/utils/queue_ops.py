# Simple queue operations
# get or put a request to queue
# blocking operation with a small timeout
import queue


def get_request(tqueue: queue.Queue, logger):
    try:
        logger.info("Waiting for request...")
        req = tqueue.get()
        return req
    except Exception as ex:
        logger.error(ex)

def put_response(response, tqueue: queue.Queue, logger):
    try:    
        logger.info("Putting request")
        tqueue.put(response)
    except Exception as ex:
        logger.error(ex)
            

# def get_request(tqueue: queue.Queue, logger):
#     while True:
#         try:
#             logger.info("Waiting for request...")
#             req = tqueue.get(True)
#             return req
#         # --if we make it nonblocking we need this exception
#         # except queue.Empty:
#         #     logger.info("Queue is empty")
#         #     continue
#         except Exception as ex:
#             logger.error(ex)
#             continue
            

# def put_response(response, tqueue: queue.Queue, logger):
#     while True:
#         try:
#             logger.info("Putting request...")
#             tqueue.put(response, True)
#             break
#         # -- if we make it nonblocking we need this exception
#         # except queue.Full:
#         #     logger.info("Queue is full")
#         except Exception as ex:
#             logger.error(ex)