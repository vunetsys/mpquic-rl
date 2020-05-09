# global imports
import os
import threading, queue
import numpy as np
import tensorflow as tf
import time
import signal

# local imports
from centraltrainer.request_handler import RequestHandler
from centraltrainer.collector import Collector
from environment.environment import Environment
from utils.logger import config_logger
from utils.queue_ops import get_request, put_response
from utils.data_transf import arrangeStateStreamsInfo, getTrainingVariables
from training import a3c
from training import load_trace

# ---------- Global Variables ----------
S_INFO = 8  # subflow_throughput_measurement, average_congestion_window_size, subflow_mean_RTT, n_unacked_packets, n_retransmitted_packets
S_LEN = 8  # take how many frames in the past
A_DIM = 2
ACTOR_LR_RATE = 0.0001
CRITIC_LR_RATE = 0.001
TRAIN_SEQ_LEN = 100  # take as a train batch
MODEL_SAVE_INTERVAL = 100
# VIDEO_BIT_RATE = [300,750,1200,1850,2850,4300]  # Kbps
PATHS = [1, 3]
BUFFER_NORM_FACTOR = 10.0
CHUNK_TIL_VIDEO_END_CAP = 48.0
M_IN_K = 1000.0
REBUF_PENALTY = 4.3  # 1 sec rebuffering -> 3 Mbps
SMOOTH_PENALTY = 1
DEFAULT_PATH = 1  # default path without agent
RANDOM_SEED = 42
RAND_RANGE = 1000000
GRADIENT_BATCH_SIZE = 16
SUMMARY_DIR = './results'
LOG_FILE = './results/log'
# log in format of time_stamp bit_rate buffer_size rebuffer_time chunk_size download_time reward
NN_MODEL = None


def agent():
    np.random.seed(RANDOM_SEED)

    assert len(PATHS) == A_DIM

    # Create results path
    if not os.path.exists(SUMMARY_DIR):
        os.makedirs(SUMMARY_DIR)

    # Spawn request handler
    tqueue = queue.Queue(1)
    rhandler = RequestHandler(1, "rhandler-thread", tqueue=tqueue, host='192.168.122.15', port='5555')
    rhandler.start()

    # Spawn collector thread
    cqueue = queue.Queue(0)
    collector = Collector(2, "collector-thread", queue=cqueue, host='192.168.122.15', port='5556')
    collector.start()

    # Spawn environment thread
    end_of_run = threading.Event()
    env = Environment(3, "environment", end_of_run)
    env.start()

    tp_list = [rhandler, collector, env]


    # Main training loop
    logger = config_logger('agent', './logs/agent.log')
    logger.info("Run Agent until training stops...")

    with tf.Session() as sess, open(LOG_FILE, 'wb') as log_file:
        # actor = a3c.ActorNetwork(sess,
        #                          state_dim=[S_INFO, S_LEN], action_dim=A_DIM,
        #                          learning_rate=ACTOR_LR_RATE)

        # critic = a3c.CriticNetwork(sess,
        #                            state_dim=[S_INFO, S_LEN],
        #                            learning_rate=CRITIC_LR_RATE)

        # summary_ops, summary_vars = a3c.build_summaries()

        # sess.run(tf.global_variables_initializer())
        # writer = tf.summary.FileWriter(SUMMARY_DIR, sess.graph)  # training monitor
        # saver = tf.train.Saver()  # save neural net parameters

        # # restore neural net parameters
        # nn_model = NN_MODEL
        # if nn_model is not None:  # nn_model is the path to file
        #     saver.restore(sess, nn_model)
        #     print("Model restored.")

        # epoch = 0
        # time_stamp = 0

        # last_path = DEFAULT_PATH
        # path = DEFAULT_PATH

        # action_vec = np.zeros(A_DIM)
        # action_vec[bit_rate] = 1

        # s_batch = [np.zeros((S_INFO, S_LEN))]
        # a_batch = [action_vec]
        # r_batch = []
        # entropy_record = []

        # actor_gradient_batch = []
        # critic_gradient_batch = []
        
        list_states = []
        while not end_of_run.is_set():
            request = get_request(tqueue, logger, end_of_run=end_of_run)

            if request is None and end_of_run.is_set():
                logger.info("END_OF_RUN is set, BATCH UPDATE")

                # get all stream_info from collector's queue
                stream_info = []
                with cqueue.mutex:
                    for elem in list(cqueue.queue):
                        stream_info.append(elem)
                    # clear the queue
                    cqueue.queue.clear()

                # Validate
                logger.info("len(list_states) {} == len(stream_info) {}".format(len(list_states), len(stream_info)))
                stream_info = arrangeStateStreamsInfo(list_states, stream_info)
                for i, stream in enumerate(stream_info):
                    logger.info(stream)
                    logger.info(list_states[i]) # print this on index based


                # get next bdw from env
                bdw_path1, bdw_path2 = env.session.getCurrentBandwidth()
                logger.info("bdw_path1: {}, bdw_path2: {}".format(bdw_path1, bdw_path2))

                
                # Proceed to next run
                stream_info.clear()
                list_states.clear()
                end_of_run.clear()
            else:
                list_states.append(request)

                path1_smoothed_RTT, path1_bandwidth, path1_packets, \
                path1_retransmissions, path1_losses, \
                path2_smoothed_RTT, path2_bandwidth, path2_packets, \
                path2_retransmissions, path2_losses, \
                    = getTrainingVariables(request) # replace later with get_request call

                # reward is aggregated bandwidth minus avg smoothed RTT minus - aggr packet losses 
                aggr_bandwidth = path1_bandwidth + path2_bandwidth
                avg_smooth_rtt = (path1_smoothed_RTT + path2_smoothed_RTT) / 2.0
                aggr_lost_packets = path1_losses + path2_losses
                a = 0.5 
                b = 0.1
                reward = aggr_bandwidth - (a * avg_smooth_rtt) - (b * aggr_lost_packets) 

                # test reward
                logger.info("Reward this round {}".format(reward))

                # the action is from the last decision
                # this is to make the framework similar to the real
                # delay, sleep_time, buffer_size, rebuf, \
                # video_chunk_size, next_video_chunk_sizes, \
                # end_of_video, video_chunk_remain = \
                #     net_env.get_video_chunk(bit_rate)

                # time_stamp += delay  # in ms
                # time_stamp += sleep_time  # in ms

                response = [request['StreamID'], request['Path1']['PathID']]
                response = [str(r).encode('utf-8') for r in response]
                time.sleep(0.2)

                put_response(response, tqueue, logger)
            time.sleep(0.01)

    # send kill signal to all
    env.stopenv()
    rhandler.stophandler()
    collector.stophandler()

    # wait for threads and process to finish gracefully...
    for tp in tp_list:
        tp.join()
    

def main():
    agent()


if __name__ == '__main__':
    main()
