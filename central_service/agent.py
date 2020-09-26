# global imports
import os
import threading, queue
import multiprocessing as mp
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
from utils.data_transf import arrangeStateStreamsInfo, getTrainingVariables, allUnique
from training import a3c
from training import load_trace

# ---------- Global Variables ----------
S_INFO = 6  # bandwidth_path_i, path_i_mean_RTT, path_i_retransmitted_packets + path_i_lost_packets
S_LEN = 8  # take how many frames in the past
A_DIM = 2 # two actions -> path 1 or path 2
ACTOR_LR_RATE = 0.0001
CRITIC_LR_RATE = 0.001
# TRAIN_SEQ_LEN = 100  # take as a train batch
TRAIN_SEQ_LEN = 100 # take as a train batch
MODEL_SAVE_INTERVAL = 64
PATHS = [1, 3] # correspond to path ids
DEFAULT_PATH = 1  # default path without agent
RANDOM_SEED = 42
RAND_RANGE = 1000000
GRADIENT_BATCH_SIZE = 8

SUMMARY_DIR = ''
LOG_FILE = ''
NN_MODEL = ''
EPOCH = 0

SSH_HOST = '192.168.122.157'


def environment(bdw_paths: mp.Array, stop_env: mp.Event, end_of_run: mp.Event):
    rhostname = 'mininet' + '@' + SSH_HOST
    
    config = {
        'server': 'ipc:///tmp/zmq',
        'client': 'tcp://*:5555',
        'publisher': 'tcp://*:5556',
        'subscriber': 'ipc:///tmp/pubsub'
    }
    logger = config_logger('environment', filepath='./logs/environment.log')
    env = Environment(bdw_paths, logger=logger, mconfig=config, remoteHostname=rhostname)

    # Lets measure env runs in time
    while not stop_env.is_set():

        # Only the agent can unblock this loop, after a training-batch has been completed
        while not end_of_run.is_set():
            try:
                # update environment config from session
                if env.updateEnvironment() == -1:
                    stop_env.set()
                    end_of_run.set()
                    break

                # run a single session & measure
                #-------------------
                now = time.time() 
                env.run()
                end = time.time()
                #-------------------

                diff = int (end - now)
                logger.debug("Time to execute one run: {}s".format(diff))

                end_of_run.set() # set the end of run so our agent knows
                # env.spawn_middleware() # restart middleware 
            except Exception as ex:
                logger.error(ex)
                break
        time.sleep(0.1)

    env.close()
        

def agent():
    np.random.seed(RANDOM_SEED)

    # Create results path
    if not os.path.exists(SUMMARY_DIR):
        os.makedirs(SUMMARY_DIR)

    # Spawn request handler
    tqueue = queue.Queue(1)
    rhandler = RequestHandler(1, "rhandler-thread", tqueue=tqueue, host=SSH_HOST, port='5555')
    rhandler.start()

    # Spawn collector thread
    cqueue = queue.Queue(0)
    collector = Collector(2, "collector-thread", queue=cqueue, host=SSH_HOST, port='5556')
    collector.start()

    # Spawn environment # process -- not a thread
    bdw_paths = mp.Array('i', 2)
    stop_env = mp.Event()
    end_of_run = mp.Event()
    env = mp.Process(target=environment, args=(bdw_paths, stop_env, end_of_run))
    env.start()

    # keep record of threads and processes
    tp_list = [rhandler, collector, env]


    # Main training loop
    logger = config_logger('agent', './logs/agent.log')
    logger.info("Run Agent until training stops...")

    with tf.Session() as sess, open(LOG_FILE, 'w') as log_file:
        actor = a3c.ActorNetwork(sess,
                                 state_dim=[S_INFO, S_LEN], action_dim=A_DIM,
                                 learning_rate=ACTOR_LR_RATE)

        critic = a3c.CriticNetwork(sess,
                                   state_dim=[S_INFO, S_LEN],
                                   learning_rate=CRITIC_LR_RATE)

        summary_ops, summary_vars = a3c.build_summaries()

        sess.run(tf.global_variables_initializer())
        writer = tf.summary.FileWriter(SUMMARY_DIR, sess.graph)  # training monitor
        saver = tf.train.Saver()  # save neural net parameters

        # # restore neural net parameters
        nn_model = NN_MODEL
        if nn_model is not None:  # nn_model is the path to file
            saver.restore(sess, nn_model)
            print("Model restored.")

        epoch = EPOCH
        time_stamp = 0

        path = DEFAULT_PATH

        action_vec = np.zeros(A_DIM)
        action_vec[path] = 1

        s_batch = [np.zeros((S_INFO, S_LEN))]
        a_batch = [action_vec]
        r_batch = []
        entropy_record = []

        actor_gradient_batch = []
        critic_gradient_batch = []
        
        list_states = []
        while not end_of_run.is_set():
            # Get scheduling request from rhandler thread
            request, ev1 = get_request(tqueue, logger, end_of_run=end_of_run)

            # end of iterations -> exit loop -> save -> bb
            if stop_env.is_set():
                break

            if request is None and end_of_run.is_set():
                logger.info("END_OF_RUN => BATCH UPDATE")

                # get all stream_info from collector's queue
                stream_info = []
                with cqueue.mutex:
                    for elem in list(cqueue.queue):
                        stream_info.append(elem)
                    # clear the queue
                    cqueue.queue.clear()

                # Validate
                # Proceed to next run
                # logger.info("len(list_states) {} == len(stream_info) {}".format(len(list_states), len(stream_info)))
                if len(list_states) != len(stream_info) or len(list_states) == 0:
                    entropy_record = []
                    del s_batch[:]
                    del a_batch[:]
                    del r_batch[:]
                    stream_info.clear()
                    list_states.clear()
                    end_of_run.clear()
                    time.sleep(0.01)
                    continue

                # Re-order rewards
                stream_info = arrangeStateStreamsInfo(list_states, stream_info)
                list_ids = [stream['StreamID'] for stream in stream_info]
                logger.info("all unique: {}".format(allUnique(list_ids, debug=True)))
                
                # for i, stream in enumerate(stream_info):
                #     logger.info(stream)
                #     logger.info(list_states[i]) # print this on index based

                # For each stream calculate a reward
                completion_times = []
                for index,stream in enumerate(stream_info):
                    path1_smoothed_RTT, path1_bandwidth, path1_packets, \
                    path1_retransmissions, path1_losses, \
                    path2_smoothed_RTT, path2_bandwidth, path2_packets, \
                    path2_retransmissions, path2_losses, \
                        = getTrainingVariables(list_states[index])

                    normalized_bwd_path0 = (bdw_paths[0] - 1.0) / (100.0 - 1.0)
                    normalized_bwd_path1 = (bdw_paths[1] - 1.0) / (100.0 - 1.0)
                    normalized_srtt_path0 = ((path1_smoothed_RTT * 1000.0) - 1.0) / (120.0)
                    normalized_srtt_path1 = ((path2_smoothed_RTT * 1000.0) - 1.0) / (120.0)
                    normalized_loss_path0 = ((path1_retransmissions + path1_losses) - 0.0) / 20.0
                    normalized_loss_path1 = ((path2_retransmissions + path2_losses) - 0.0) / 20.0

                    # aggr_bdw = normalized_bwd_path0 + normalized_bwd_path1
                    aggr_srtt = normalized_srtt_path0 + normalized_srtt_path1
                    aggr_loss = normalized_loss_path0 + normalized_loss_path1

                    reward = (a_batch[index][0]* normalized_bwd_path0 + a_batch[index][1]*normalized_bwd_path1) - stream['CompletionTime'] - (0.8*aggr_srtt) - (1.0 * aggr_loss)
                    r_batch.append(reward)
                    completion_times.append(stream['CompletionTime'])

                # Check if we have a stream[0] = 0 add -> 0 to r_batch
                tmp_s_batch = np.stack(s_batch[:], axis=0)
                tmp_r_batch = np.vstack(r_batch[:])
                if tmp_s_batch.shape[0] > tmp_r_batch.shape[0]:
                    logger.debug("s_batch({}) > r_batch({})".format(tmp_s_batch.shape[0], tmp_r_batch.shape[0]))
                    logger.debug(tmp_s_batch[0])
                    r_batch.insert(0, 0)

                # Save metrics for debugging
                # log time_stamp, bit_rate, buffer_size, reward
                for index, stream in enumerate(stream_info):
                    path1_smoothed_RTT, path1_bandwidth, path1_packets, \
                    path1_retransmissions, path1_losses, \
                    path2_smoothed_RTT, path2_bandwidth, path2_packets, \
                    path2_retransmissions, path2_losses, \
                        = getTrainingVariables(list_states[index])
                    log_file.write(str(time_stamp) + '\t' +
                                str(PATHS[path]) + '\t' +
                                str(bdw_paths[0]) + '\t' +
                                str(bdw_paths[1]) + '\t' +
                                str(path1_smoothed_RTT) + '\t' +
                                str(path2_smoothed_RTT) + '\t' +
                                str(path1_retransmissions+path1_losses) + '\t' +
                                str(path2_retransmissions+path2_losses) + '\t' +
                                str(stream['CompletionTime']) + '\t' +
                                str(stream['Path']) + '\n')
                    log_file.flush()
                    time_stamp += 1

                # Single Training step
                # ----------------------------------------------------------------------------------------------------
                actor_gradient, critic_gradient, td_batch = \
                    a3c.compute_gradients(s_batch=np.stack(s_batch[1:], axis=0),  # ignore the first chuck
                                        a_batch=np.vstack(a_batch[1:]),  # since we don't have the
                                        r_batch=np.vstack(r_batch[1:]),  # control over it
                                        terminal=True, actor=actor, critic=critic)
                td_loss = np.mean(td_batch)

                actor_gradient_batch.append(actor_gradient)
                critic_gradient_batch.append(critic_gradient)

                logger.debug ("====")
                logger.debug ("Epoch: {}".format(epoch))
                msg = "TD_loss: {}, Avg_reward: {}, Avg_entropy: {}".format(td_loss, np.mean(r_batch[1:]), np.mean(entropy_record[1:]))
                logger.debug (msg)
                logger.debug ("====")
                # ----------------------------------------------------------------------------------------------------

                # Print summary for tensorflow
                # ----------------------------------------------------------------------------------------------------
                summary_str = sess.run(summary_ops, feed_dict={
                        summary_vars[0]: td_loss,
                        summary_vars[1]: np.mean(r_batch),
                        summary_vars[2]: np.mean(entropy_record),
                        summary_vars[3]: np.mean(completion_times)
                    })

                writer.add_summary(summary_str, epoch)
                writer.flush()
                # ----------------------------------------------------------------------------------------------------

                # Update gradients
                if len(actor_gradient_batch) >= GRADIENT_BATCH_SIZE:
                    assert len(actor_gradient_batch) == len(critic_gradient_batch)

                    for i in range(len(actor_gradient_batch)):
                        actor.apply_gradients(actor_gradient_batch[i])
                        critic.apply_gradients(critic_gradient_batch[i])

                    epoch += 1
                    if epoch % MODEL_SAVE_INTERVAL == 0:
                        save_path = saver.save(sess, SUMMARY_DIR + "/nn_model_ep_" + str(epoch) + ".ckpt")

                entropy_record = []

                # Clear all before proceeding to next run
                del s_batch[:]
                del a_batch[:]
                del r_batch[:]
                stream_info.clear()
                list_states.clear()
                end_of_run.clear()
            else:
                ev1.set() # let `producer` (rh) know we received request
                list_states.append(request)

                # The bandwidth metrics coming from MPQUIC are not correct
                # constant values not upgraded
                path1_smoothed_RTT, path1_bandwidth, path1_packets, \
                path1_retransmissions, path1_losses, \
                path2_smoothed_RTT, path2_bandwidth, path2_packets, \
                path2_retransmissions, path2_losses, \
                    = getTrainingVariables(request)

                time_stamp += 1  # in ms
                last_path = path

                # retrieve previous state
                if len(s_batch) == 0:
                    state = np.zeros((S_INFO, S_LEN))
                else:
                    state = np.array(s_batch[-1], copy=True)

                # dequeue history record
                state = np.roll(state, -1, axis=1)

                # this should be S_INFO number of terms
                state[0, -1] = (bdw_paths[0] - 1.0) / (100.0 - 1.0) # bandwidth path1
                state[1, -1] = (bdw_paths[1] - 1.0) / (100.0 - 1.0) # bandwidth path2
                state[2, -1] = ((path1_smoothed_RTT * 1000.0) - 1.0) / (120.0) # max RTT so far 120ms 
                state[3, -1] = ((path2_smoothed_RTT * 1000.0) - 1.0) / (120.0)
                state[4, -1] = ((path1_retransmissions + path1_losses) - 0.0) / 20.0
                state[5, -1] = ((path2_retransmissions + path2_losses) - 0.0) / 20.0

                s_batch.append(state)

                action_prob = actor.predict(np.reshape(state, (1, S_INFO, S_LEN)))
                action_cumsum = np.cumsum(action_prob)
                path = (action_cumsum > np.random.randint(1, RAND_RANGE) / float(RAND_RANGE)).argmax()

                action_vec = np.zeros(A_DIM)
                action_vec[path] = 1
                a_batch.append(action_vec)

                logger.debug("PATH: {}".format(path))

                entropy_record.append(a3c.compute_entropy(action_prob[0]))

                # prepare response
                response = [request['StreamID'], PATHS[path]]
                response = [str(r).encode('utf-8') for r in response]
                ev2 = threading.Event()
                put_response((response, ev2), tqueue, logger)
                ev2.wait() # blocks until `consumer` (i.e. rh) receives response

    # send kill signal to all
    stop_env.set()
    rhandler.stophandler()
    collector.stophandler()

    # wait for threads and process to finish gracefully...
    for tp in tp_list:
        tp.join()
    

def main():
    agent()


if __name__ == '__main__':
    main()
