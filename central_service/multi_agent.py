# global imports
import os
import threading, queue
import multiprocessing as mp
import logging
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
TRAIN_SEQ_LEN = 32 # take as a train batch
MODEL_SAVE_INTERVAL = 8
PATHS = [1, 3] # correspond to path ids
DEFAULT_PATH = 1  # default path without agent
RANDOM_SEED = 42
RAND_RANGE = 1000000
GRADIENT_BATCH_SIZE = 8
SUMMARY_DIR = './results'
LOG_FILE = './results/log'
# log in format of time_stamp bit_rate buffer_size rebuffer_time chunk_size download_time reward
NN_MODEL = None
NUM_AGENTS = 2

BASE_PORT = 5555
SSH_HOST = ['192.168.122.157', '192.168.122.15']


def central_agent(net_params_queues, exp_queues):
    assert len(net_params_queues) == NUM_AGENTS
    assert len(exp_queues) == NUM_AGENTS

    logging.basicConfig(filename=LOG_FILE + '_central',
                        filemode='w',
                        level=logging.INFO)
    
    with tf.Session() as sess, open(LOG_FILE + '_test', 'w') as test_log_file:
        actor = a3c.ActorNetwork(sess,
                                 state_dim=[S_INFO, S_LEN], action_dim=A_DIM,
                                 learning_rate=ACTOR_LR_RATE)

        critic = a3c.CriticNetwork(sess,
                                   state_dim=[S_INFO, S_LEN], 
                                   learning_rate=CRITIC_LR_RATE)

        summary_ops, summary_vars = a3c.build_summaries()

        sess.run(tf.global_variables_initializer())
        writer = tf.summary.FileWriter(SUMMARY_DIR, sess.graph) # training monitor
        saver = tf.train.Saver() # save neural net parameters

        # restore neural net parameters
        nn_model = NN_MODEL
        if nn_model is not None: # nn_model is the path to file
            saver.restore(sess, nn_model)
            print ("Model Restored.")
        
        epoch = 0

        # assemble experiences from agents, compute the gradients
        while True:
            # synchronize the network parameters of work agent
            actor_net_params = actor.get_network_params()
            critic_net_params = critic.get_network_params()
            for i in range(NUM_AGENTS):
                net_params_queues[i].put([actor_net_params, critic_net_params])
                # Note: this is synchronous version of the parallel training,
                # which is easier to understand and probe. The framework can be
                # fairly easily modified to support asynchronous training.
                # Some practices of asynchronous training (lock-free SGD at
                # its core) are nicely explained in the following two papers:
                # https://arxiv.org/abs/1602.01783
                # https://arxiv.org/abs/1106.5730
            
            # record average reward and td loss change
            # in the experiences from the agents
            total_batch_len = 0.0
            total_reward = 0.0
            total_td_loss = 0.0
            total_entropy = 0.0
            total_agents = 0.0 

            # assemble experiences from the agents
            actor_gradient_batch = []
            critic_gradient_batch = []

            for i in range(NUM_AGENTS):
                s_batch, a_batch, r_batch, terminal, info, c_times = exp_queues[i].get()

                actor_gradient, critic_gradient, td_batch = \
                    a3c.compute_gradients(
                        s_batch=np.stack(s_batch, axis=0),
                        a_batch=np.vstack(a_batch),
                        r_batch=np.vstack(r_batch),
                        terminal=terminal, actor=actor, critic=critic)

                actor_gradient_batch.append(actor_gradient)
                critic_gradient_batch.append(critic_gradient)

                total_reward += np.sum(r_batch)
                total_td_loss += np.sum(td_batch)
                total_batch_len += len(r_batch)
                total_agents += 1.0
                total_entropy += np.sum(info['entropy'])
                total_completion_time += np.sum(c_times)

            # compute aggregated gradient
            assert NUM_AGENTS == len(actor_gradient_batch)
            assert len(actor_gradient_batch) == len(critic_gradient_batch)
            # assembled_actor_gradient = actor_gradient_batch[0]
            # assembled_critic_gradient = critic_gradient_batch[0]
            # for i in xrange(len(actor_gradient_batch) - 1):
            #     for j in xrange(len(assembled_actor_gradient)):
            #             assembled_actor_gradient[j] += actor_gradient_batch[i][j]
            #             assembled_critic_gradient[j] += critic_gradient_batch[i][j]
            # actor.apply_gradients(assembled_actor_gradient)
            # critic.apply_gradients(assembled_critic_gradient)
            for i in range(len(actor_gradient_batch)):
                actor.apply_gradients(actor_gradient_batch[i])
                critic.apply_gradients(critic_gradient_batch[i])
            
            # log training information
            epoch += 1
            avg_reward = total_reward  / total_agents
            avg_td_loss = total_td_loss / total_batch_len
            avg_entropy = total_entropy / total_batch_len
            avg_completion_time = total_completion_time / total_batch_len

            logging.info('Epoch: ' + str(epoch) +
                         ' TD_loss: ' + str(avg_td_loss) +
                         ' Avg_reward: ' + str(avg_reward) +
                         ' Avg_entropy: ' + str(avg_entropy) +
                         ' Avg_completion_time: ' + str(avg_completion_time))

            summary_str = sess.run(summary_ops, feed_dict={
                summary_vars[0]: avg_td_loss,
                summary_vars[1]: avg_reward,
                summary_vars[2]: avg_entropy,
                summary_vars[3]: avg_completion_time
            })

            writer.add_summary(summary_str, epoch)
            writer.flush()

            if epoch % MODEL_SAVE_INTERVAL == 0:
                # Save the neural net parameters to disk
                save_path = saver.save(sess, SUMMARY_DIR + "/nn_model_ep_" +
                                        str(epoch) + ".ckpt")
                logging.info("Model saved in file: " + save_path)
                # some sort of testing takes place here, not in our case!
                # or not yet...


def environment():
    pass

def agent(agent_id, host, port, net_params_queue, exp_queues):
    # Spawn request handler
    tqueue = queue.Queue(1)
    rhandler = RequestHandler(1, "rhandler-thread", tqueue=tqueue, host=host, port=str(port))
    rhandler.start()

    # Spawn collector thread
    cqueue = queue.Queue(0)
    collector = Collector(2, "collector-thread", queue=cqueue, host=host, port=str(port+1))
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
    LOG_FILENAME = 'agent_{}'.format(agent_id)
    logger = config_logger('agent', './logs/{}.log'.format(LOG_FILENAME))
    logger.info("Run Agent until training stops...")

    with tf.Session() as sess, open(LOG_FILE + '_' + LOG_FILENAME, 'w') as log_file:
        actor = a3c.ActorNetwork(sess,
                                 state_dim=[S_INFO, S_LEN], action_dim=A_DIM,
                                 learning_rate=ACTOR_LR_RATE)

        critic = a3c.CriticNetwork(sess,
                                   state_dim=[S_INFO, S_LEN],
                                   learning_rate=CRITIC_LR_RATE)

        # initial synchronization of the network parameters from the coordinator
        actor_net_params, critic_net_params = net_params_queue.get()
        actor.set_network_params(actor_net_params)
        critic.set_network_params(critic_net_params)

        time_stamp = 0

        last_path = DEFAULT_PATH
        path = DEFAULT_PATH

        action_vec = np.zeros(A_DIM)
        action_vec[path] = 1

        s_batch = [np.zeros((S_INFO, S_LEN))]
        a_batch = [action_vec]
        r_batch = []
        entropy_record = []

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
                for stream in stream_info:
                    # Reward is 1 minus the square of the mean completion time
                    # This means that small completion times (1<=) get praised
                    # But large completion times (>=1) gets double the damage
                    reward = 1 - (stream['CompletionTime'] ** 2) 
                    r_batch.append(reward)
                    completion_times.append(stream['CompletionTime'])

                # Check if we have a stream[0] = 0 add -> 0 to r_batch
                tmp_s_batch = np.stack(s_batch[:], axis=0)
                tmp_r_batch = np.vstack(r_batch[:])
                # logger.debug("r_batch.shape[0]: {}rows - s_batch.shape[0]: {}rows ".format(tmp_r_batch.shape[0], tmp_s_batch.shape[0]))
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

                # Training step for div // TRAIN_SEQ_LEN (e.g. sequence => [64, 64, ..., 16]) last one is remainder
                # ----------------------------------------------------------------------------------------------------
                div  = len(r_batch) // TRAIN_SEQ_LEN
                start = 1
                end = TRAIN_SEQ_LEN
                # logger.debug("DIVISION: {}".format(div))
                for i in range(div):
                    actor_gradient, critic_gradient, td_batch = \
                        a3c.compute_gradients(s_batch=np.stack(s_batch[start:end], axis=0),  # ignore the first chuck
                                            a_batch=np.vstack(a_batch[start:end]),  # since we don't have the
                                            r_batch=np.vstack(r_batch[start:end]),  # control over it
                                            terminal=True, actor=actor, critic=critic)
                    td_loss = np.mean(td_batch)

                    actor_gradient_batch.append(actor_gradient)
                    critic_gradient_batch.append(critic_gradient)

                    logger.debug ("====")
                    logger.debug ("Epoch: {}".format(epoch))
                    msg = "TD_loss: {}, Avg_reward: {}, Avg_entropy: {}".format(td_loss, np.mean(r_batch[start:end]), np.mean(entropy_record[start:end]))
                    logger.debug (msg)
                    logger.debug ("====")

                    start   += (TRAIN_SEQ_LEN - 1)
                    end     += TRAIN_SEQ_LEN
                # ----------------------------------------------------------------------------------------------------

                # One final training step with remaining samples
                # ----------------------------------------------------------------------------------------------------
                logger.debug("FINAL TRAINING STEP")
                logger.debug("Start: {}, End: {}".format(start, end))
                # If there is a smaller difference, leave it be might introduce more noise.
                if (len(r_batch) - start) > GRADIENT_BATCH_SIZE: 
                    actor_gradient, critic_gradient, td_batch = \
                            a3c.compute_gradients(s_batch=np.stack(s_batch[start:], axis=0),  # ignore the first chuck
                                                a_batch=np.vstack(a_batch[start:]),  # since we don't have the
                                                r_batch=np.vstack(r_batch[start:]),  # control over it
                                                terminal=True, actor=actor, critic=critic)
                    td_loss = np.mean(td_batch)

                    actor_gradient_batch.append(actor_gradient)
                    critic_gradient_batch.append(critic_gradient)


                    logger.debug ("====")
                    logger.debug ("Epoch: {}".format(epoch))
                    msg = "TD_loss: {}, Avg_reward: {}, Avg_entropy: {}".format(td_loss, np.mean(r_batch[start:end]), np.mean(entropy_record[start:end]))
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

                # get bdw from env - multiprocessing.sharedMemory/bdw_paths/array
                # logger.info("bdw_path1: {}, bdw_path2: {}".format(bdw_paths[0], bdw_paths[1]))

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
                # state[6, -1] = path1_losses
                # state[7, -1] = path2_losses

                s_batch.append(state)

                action_prob = actor.predict(np.reshape(state, (1, S_INFO, S_LEN)))
                action_cumsum = np.cumsum(action_prob)
                path = (action_cumsum > np.random.randint(1, RAND_RANGE) / float(RAND_RANGE)).argmax()

                action_vec = np.zeros(A_DIM)
                action_vec[path] = 1
                a_batch.append(action_vec)

                logger.debug("PATH: {}".format(path))

                entropy_record.append(a3c.compute_entropy(action_prob[0]))

                # log time_stamp, bit_rate, buffer_size, reward
                log_file.write(str(time_stamp) + '\t' +
                            str(PATHS[path]) + '\t' +
                            str(bdw_paths[0]) + '\t' +
                            str(bdw_paths[1]) + '\t' +
                            str(path1_smoothed_RTT) + '\t' +
                            str(path2_smoothed_RTT) + '\t' + 
                            str(path1_retransmissions + path1_losses) + '\t' +
                            str(path2_retransmissions + path2_losses) + '\t\n')
                log_file.flush()

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
    np.random.seed(RANDOM_SEED)

    assert len(PATHS) == A_DIM

    # create result directory
    if not os.path.exists(SUMMARY_DIR):
        os.makedirs(SUMMARY_DIR)

    # inter-process communication queues
    net_params_queues = []
    exp_queues = []
    for i in range(NUM_AGENTS):
        net_params_queues.append(mp.Queue(1))
        exp_queues.append(mp.Queue(1))

    # create a coordinator and multiple agent processes
    # (note: threading is not desirable due to python GIL)
    coordinator = mp.Process(target=central_agent,
                             args=(net_params_queues, exp_queues))
    coordinator.start()

    agents = []
    for i in range(NUM_AGENTS):
        host = SSH_HOST[i]
        port = BASE_PORT
        agents.append(mp.Process(target=agent,
                                 args=(i,
                                       host,
                                       port,
                                       net_params_queues[i],
                                       exp_queues[i])))
        BASE_PORT += 2 # ports: 5555, 5556, 5557, 5558

    for i in range(NUM_AGENTS):
        agents[i].start()

    # wait unit training is done
    coordinator.join()


if __name__ == "__main__":
    main()