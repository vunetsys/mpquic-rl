import tensorflow as tf
import numpy as np
import zmq
import os
import time
import sys
import json
import a3c

# ---------- Global Variables ----------
S_INFO = 6  # bandwidth_path_i, path_i_mean_RTT, path_i_retransmitted_packets + path_i_lost_packets
S_LEN = 8  # take how many frames in the past
A_DIM = 2 # two actions -> path 1 or path 2
ACTOR_LR_RATE = 0.0001
CRITIC_LR_RATE = 0.001
# TRAIN_SEQ_LEN = 100  # take as a train batch
TRAIN_SEQ_LEN = 100 # take as a train batch
MODEL_SAVE_INTERVAL = 128
PATHS = [1, 3] # correspond to path ids
DEFAULT_PATH = 1  # default path without agent
RANDOM_SEED = 42
RAND_RANGE = 1000000
GRADIENT_BATCH_SIZE = 8

currDir = os.getcwd() + '/git/nn_testing'
SUMMARY_DIR = currDir + '/results'
LOG_FILE = currDir + '/results/log'
NN_MODEL = currDir + ''
# NN_MODEL = None
EPOCH = 0 # global epoch for initial value


def getTrainingVariables(request):
    '''
        Return all necessary state/training variables from the request
        They might come in random order so rotate them
    '''
    if request['Path1']['PathID'] == 1:
        return request['Path1']['SmoothedRTT'], request['Path1']['Bandwidth'], request['Path1']['Packets'], \
            request['Path1']['Retransmissions'], request['Path1']['Losses'], \
            request['Path2']['SmoothedRTT'], request['Path2']['Bandwidth'], request['Path2']['Packets'], \
            request['Path2']['Retransmissions'], request['Path2']['Losses']
    else:
        return request['Path2']['SmoothedRTT'], request['Path2']['Bandwidth'], request['Path2']['Packets'], \
            request['Path2']['Retransmissions'], request['Path2']['Losses'], \
            request['Path1']['SmoothedRTT'], request['Path1']['Bandwidth'], request['Path1']['Packets'], \
            request['Path1']['Retransmissions'], request['Path1']['Losses']


def handle_requests(host, bdw_path1, bdw_path2):
    np.random.seed(RANDOM_SEED)

    if not os.path.exists(SUMMARY_DIR):
        os.makedirs(SUMMARY_DIR)

    with tf.Session() as sess, open(LOG_FILE, 'w') as log_file:
        actor = a3c.ActorNetwork(sess,
                                state_dim=[S_INFO, S_LEN], action_dim=A_DIM,
                                learning_rate=ACTOR_LR_RATE)
        
        sess.run(tf.initialize_all_variables())
        saver = tf.train.Saver()

        nn_model = NN_MODEL
        if nn_model is not None:
            saver.restore(sess, nn_model)
            print("Model restored.")

        init_action = np.zeros(A_DIM)
        init_action[DEFAULT_PATH] = 0

        s_batch = [np.zeros((S_INFO, S_LEN))]

        # ZMQ Context
        context = zmq.Context()
        server = context.socket(zmq.REP)
        server.bind(host)

        poller = zmq.Poller()
        poller.register(server, zmq.POLLIN)

        while True:
            if (poller.poll(timeout=10)):
		#---- log time ----
                start = time.time()
                request = server.recv_multipart(zmq.NOBLOCK)
                json_request = json.loads(request[1])

                path1_smoothed_RTT, path1_bandwidth, path1_packets, \
                path1_retransmissions, path1_losses, \
                path2_smoothed_RTT, path2_bandwidth, path2_packets, \
                path2_retransmissions, path2_losses, \
                    = getTrainingVariables(json_request)

                if len(s_batch) == 0:
                    state = np.zeros((S_INFO, S_LEN))
                else:
                    state = np.array(s_batch[-1], copy=True)

                # dequeue history record
                state = np.roll(state, -1, axis=1)

                  # this should be S_INFO number of terms
                state[0, -1] = (bdw_path1 - 1.0) / (100.0 - 1.0) # bandwidth path1
                state[1, -1] = (bdw_path2 - 1.0) / (100.0 - 1.0) # bandwidth path2
                state[2, -1] = ((path1_smoothed_RTT * 1000.0) - 1.0) / (120.0) # max RTT so far 120ms 
                state[3, -1] = ((path2_smoothed_RTT * 1000.0) - 1.0) / (120.0)
                state[4, -1] = ((path1_retransmissions + path1_losses) - 0.0) / 20.0
                state[5, -1] = ((path2_retransmissions + path2_losses) - 0.0) / 20.0

                s_batch.append(state)

                # get prediction
                action_prob = actor.predict(np.reshape(state, (1, S_INFO, S_LEN)))
                action_cumsum = np.cumsum(action_prob)
                path = (action_cumsum > np.random.randint(1, RAND_RANGE) / float(RAND_RANGE)).argmax()

                # give back response
                response = [json_request['StreamID'], PATHS[path]]
                response = [str(r).encode('utf-8') for r in response]
                server.send_multipart(response)

		#---- log time ----
                end = time.time()
                diff = end - start

                # log 
                log_file.write(str(diff) + '\t' +
                                str(PATHS[path]) + '\t' +
                                str(bdw_path1) + '\t' +
                                str(bdw_path2) + '\t' +
                                str(path1_smoothed_RTT) + '\t' +
                                str(path2_smoothed_RTT) + '\t' +
                                str(path1_retransmissions+path1_losses) + '\t' +
                                str(path2_retransmissions+path2_losses) + '\t\n')
                log_file.flush()


def main():
    assert len(sys.argv) == 3
    bdws= sys.argv[1:]
    handle_requests('ipc:///tmp/zmq', int(bdws[0]), int(bdws[1]))


if __name__ == "__main__":
    main()
