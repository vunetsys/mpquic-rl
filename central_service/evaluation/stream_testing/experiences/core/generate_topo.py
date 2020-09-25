# from __future__ import print_function

import math

LEFT_SUBNET = "leftSubnet"
RIGHT_SUBNET = "rightSubnet"
TOPO_TYPE = "topoType"
PATHS = "paths"
NETEM = "netem"

DEFAULT_LEFT_SUBNET = "10.0."
DEFAULT_RIGHT_SUBNET = "10.1."
DEFAULT_TOPO_TYPE = "MultiIf"
DEFAULT_PATHS = [{}, {}]
DEFAULT_NETEM = []

""" Path info """
DELAY = "delay"
QUEUE_SIZE = "queueSize"
BANDWIDTH = "bandwidth"
LOSS = "loss"
QUEUING_DELAY = "queuingDelay"

# In ms, RTT = 2 * delay
DEFAULT_DELAY = 15
# In number of packets
# DEFAULT_QUEUE_SIZE = 10
# In Mbps
DEFAULT_BANDWIDTH = 10
DEFAULT_LOSS = 0.0
DEFAULT_QUEUING_DELAY = 1.0

DEFAULT_MTU = 1500


def bandwidthDelayProductDividedByMSS(bandwidth, delay, mss):
    rtt = 2 * float(delay)
    """ Since bandwidth is in Mbps and rtt in ms """
    bandwidthDelayProduct = (float(bandwidth) * 125000.0) * (rtt / 1000.0)
    return int(math.ceil(bandwidthDelayProduct * 1.0 / mss))


def bdpBufferWithQueuingDelay(bandwidth, delay, mtu, queuingDelay):
    rtt = 2 * float(delay)
    max_queue_size = int(float(rtt) * float(bandwidth) * 1024 * 1024 / (int(mtu) * 8 * 1000))
    max_queue_size += int(float(queuingDelay) * float(bandwidth) * 1024 * 1024 / (int(mtu) * 8 * 1000))
    if max_queue_size <= 10:
        max_queue_size = 10

    return max_queue_size


def generateTopoFile(topoFilename, topoDict):
    topoFile = open(topoFilename, 'w')
    print(LEFT_SUBNET + ":" + topoDict.get(LEFT_SUBNET, DEFAULT_LEFT_SUBNET), file=topoFile)
    print(RIGHT_SUBNET + ":" + topoDict.get(RIGHT_SUBNET, DEFAULT_RIGHT_SUBNET), file=topoFile)
    print(TOPO_TYPE + ":" + topoDict.get(TOPO_TYPE, DEFAULT_TOPO_TYPE), file=topoFile)
    pathNumber = 0
    for pathInfo in topoDict.get(PATHS, DEFAULT_PATHS):
        """ pathInfo is a dict """
        delay = str(pathInfo.get(DELAY, DEFAULT_DELAY))
        bandwidth = str(pathInfo.get(BANDWIDTH, DEFAULT_BANDWIDTH))
        if QUEUING_DELAY in pathInfo:
            queueSize = str(bandwidth)
            #queueSize = str(bdpBufferWithQueuingDelay(bandwidth, delay, DEFAULT_MTU, float(pathInfo[QUEUING_DELAY])))
        else:
            queueSize = str(bandwidth)
            #queueSize = str(pathInfo.get(QUEUE_SIZE, int(max(DEFAULT_QUEUING_DELAY * bandwidthDelayProductDividedByMSS(bandwidth, delay, DEFAULT_MTU),10))))
        loss = str(pathInfo.get(LOSS, DEFAULT_LOSS))
        print("path_" + str(pathNumber) + ":" + delay + "," + queueSize + "," + bandwidth + "," + loss, file=topoFile)
        """ Don't forget to increment pathNumber! """
        pathNumber += 1

    print("changeNetem:yes", file=topoFile)
    if len(topoDict.get(NETEM, DEFAULT_NETEM)) > 0:
        for netemInfo in topoDict.get(NETEM, DEFAULT_NETEM):
            """ netemInfo is a iterable (tuple or list) of form (path_id, timeAt, command) """
            print("netemAt_" + str(netemInfo[0]) + ":" + str(netemInfo[1]) + "," + str(netemInfo[2]), file=topoFile)

    topoFile.close()


if __name__ == '__main__':
    topoDict = {
        PATHS: [{DELAY: 35, QUEUE_SIZE: 15}, {BANDWIDTH: 20}, {DELAY: 10, BANDWIDTH: 1}],
        NETEM: [(1, 3, "loss 1%")]
    }
    generateTopoFile("my_topo", topoDict)
