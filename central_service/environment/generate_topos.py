import json
import numpy as np


from experiences.core.generate_topo import PATHS, NETEM, BANDWIDTH, DELAY, QUEUING_DELAY

from experiences.core.generate_xp import XP_TYPE, SCHEDULER_CLIENT, SCHEDULER_SERVER, CC, \
    CLIENT_PCAP, SERVER_PCAP, HTTPS_FILE, HTTPS_RANDOM_SIZE, QUIC_MULTIPATH, RMEM, \
    QUIC, HTTPS, WEB_BROWSE, JSON_FILE, PROJECT, PATH_SCHEDULER, BROWSER, SINGLE_FILE, \
    PRIORITY_HIGH, PRIORITY_LOW, DEPENDENCY_1, DEPENDENCY_2, HTTPS_RANDOM_SIZE2, \
    HTTPS_RANDOM_SIZE3, HTTPS_RANDOM_SIZE4, PRIORITY_3, PRIORITY_4, MULTIFILE, \
    HTTPS_RANDOM_SIZE5, PRIORITY_5


TOPOS_JSON_FILE='./environment/topos.json'


def generateExperimentalDesignRandomTopos(nbMptcpTopos=10, pathsPerTopo=2, bandwidth=(1, 100), rtt=(0, 50), queuingDelay=(0.0, 0.1), loss=(0.0, 2.5)):
    """ Assume only two paths per MPTCP topology, uniform distribution """
    mptcpTopos = []
    for _ in range(nbMptcpTopos):
        mptcpTopo = {PATHS: [], NETEM: []}
        for nbPath in range(pathsPerTopo):
            bandwidthPath = "{0}".format(np.random.randint(low=bandwidth[0], high=bandwidth[1]))
            # bandwidthPath = "{0:.2f}".format(np.random.uniform(low=bandwidth[0], high=bandwidth[1]))
            rttPath = "{0:.0f}".format(np.random.uniform(low=rtt[0], high=rtt[1]))
            delayPath = "{0:.1f}".format(float(rttPath) / 2.0)
            lossPath = "{0:.2f}".format(np.random.uniform(low=loss[0], high=loss[1]))
            queuingDelayPath = "{0:.3f}".format(np.random.uniform(low=queuingDelay[0], high=queuingDelay[1]))
            # tcpTopos.append({PATHS: [{BANDWIDTH: bandwidthPath, DELAY: delayPath}], NETEM: [(0, 0, "loss " + str(lossPath) + "%")]})
            mptcpTopo[PATHS].append({BANDWIDTH: bandwidthPath, DELAY: delayPath, QUEUING_DELAY: queuingDelayPath})
            mptcpTopo[NETEM].append((nbPath, 0, "loss " + str(lossPath) + "%"))

        mptcpTopos.append(mptcpTopo)
        reversedMptcpTopoPaths = mptcpTopo[PATHS][::-1]
        reversedMptcpTopoNetem = []
        nbPath = 0
        for netem in mptcpTopo[NETEM][::-1]:
            reversedMptcpTopoNetem.append((nbPath, netem[1], netem[2]))
            nbPath += 1

        reversedMptcpTopo = {PATHS: reversedMptcpTopoPaths, NETEM: reversedMptcpTopoNetem}
        # this line appends the mptcpTopos the other way around
        # mptcpTopos.append(reversedMptcpTopo)

    return mptcpTopos


def saveToposJSON():
    mptcpTopos = generateExperimentalDesignRandomTopos(nbMptcpTopos=100)
    with open(TOPOS_JSON_FILE, 'w') as fp:
        json.dump(mptcpTopos, fp, indent=4)


def loadToposJSON(fpath=TOPOS_JSON_FILE):
    with open(fpath, 'r') as fp:
        mptcpTopos = json.load(fp)

    return mptcpTopos


if __name__ == "__main__":
    '''Basic test'''
    saveToposJSON()
    loadToposJSON()