'''
    TODO: Write a proper explanation :P
'''

# global imports
import json
import random
import time
import os

# local imports
from experiences.quic_web_browse import launchTests


# global vars
TOPOS_FP = './topos.json'
GRAPHS_FP = './test_graphs.json'
TG_PAIRS = './pairs_topos_graphs.json'
random.seed(42)


def getNetemToTuple(topo):
    '''in json -> tuple (0 0 loss 1.69%) is stored as [0, 0, loss 1.69%]
        revert it back to tuple, otherwise error is produced
    '''
    topo[0]['netem'][0] = (topo[0]['netem'][0][0], topo[0]['netem'][0][1], topo[0]['netem'][0][2])
    topo[0]['netem'][1] = (topo[0]['netem'][1][0], topo[0]['netem'][1][1], topo[0]['netem'][1][2])
    return topo


def load_or_generate_pairs():
    if not os.path.isfile(TG_PAIRS):
        with open(TOPOS_FP, 'r') as fp:
            topos = json.load(fp)
        with open(GRAPHS_FP, 'r') as fp:
            graphs = json.load(fp)

        tuple_list = []
        for i in range(len(topos)):
            for j in range(len(graphs)):
                tuple_list.append((i, j))

        pairs = random.sample(tuple_list, 100)
        output = []
        for (t, g) in pairs:
            pair = {
                'graph': graphs[g],
                'topo': topos[t]
            }
            output.append(pair)
        with open(TG_PAIRS, 'w') as fp:
            json.dump(output, fp, indent=4)
        return output
    else:
        with open(TG_PAIRS, 'r') as fp:
            pairs = json.load(fp)
        return pairs       
            

def spawn_nn_inference():
    import subprocess
    PYTHON_NN_INFERENCE = './go/bin/middleware'

    def send_cmd(cmd):
        REMOTE_PORT = '8022'
        REMOTE_HOST = 'mininet@192.168.122.157'
        ssh_cmd = ["ssh", "-p", REMOTE_PORT, REMOTE_HOST, cmd]
        subprocess.Popen(ssh_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=False)
    
    send_cmd("killall {}".format(PYTHON_NN_INFERENCE))
    time.sleep(0.5)
    send_cmd(PYTHON_NN_INFERENCE)


def main():
    pairs = load_or_generate_pairs()

    counter = 1
    with open('./batch_run_rl.txt', 'w') as fp:
        for p in pairs:
            graph = p['graph']['file']
            topo = getNetemToTuple([p['topo']])

            fp.write("{},\t{},\t{}\n".format(counter, graph, p['topo']))
            counter += 1

            try:
                start = time.time()
                launchTests(topo, graph)
                end = time.time()

                diff = int(start - end)
                print("runtime: {}s".format(diff))
            except Exception as ex:
                print (ex)



if __name__ == "__main__":
    main()