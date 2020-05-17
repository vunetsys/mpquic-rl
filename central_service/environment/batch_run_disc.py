'''
    Script that will run all train_graph.json tests and check if they are valid
    e.g., no errors produced, no discrepancies 

    disc is from disconnected and the reason is that this script is not part of the training.
'''


import json
import random
import time

from experiences.quic_web_browse import launchTests




TOPOS_FP = './topos.json'
GRAPHS_FP = './train_graphs.json'
random.seed(42)

def getNetemToTuple(topo):
    '''in json -> tuple (0 0 loss 1.69%) is stored as [0, 0, loss 1.69%]
        revert it back to tuple, otherwise error is produced
    '''
    topo[0]['netem'][0] = (topo[0]['netem'][0][0], topo[0]['netem'][0][1], topo[0]['netem'][0][2])
    topo[0]['netem'][1] = (topo[0]['netem'][1][0], topo[0]['netem'][1][1], topo[0]['netem'][1][2])
    return topo


with open(TOPOS_FP, 'r') as fp:
    topos = json.load(fp)

with open(GRAPHS_FP, 'r') as fp:
    graphs = json.load(fp)

counter = 0
with open('./batch_run.txt', 'w') as fp:
    for graph in graphs:
        itopo = getNetemToTuple([topos[random.randint(0, len(topos)-1)]])
        g = graph['file']

        counter += 1
        msg = "Run {}, g {}, itopo {}\n".format(counter, g, itopo)
        fp.write(msg)

        # run one test
        try:
            start = time.time()
            launchTests(itopo, g)
            end = time.time()

            diff = int(start - end)
            print("Time to execute one run: {}s".format(diff))
        except Exception as ex:
            print ("Exception")
            print (ex)
    
