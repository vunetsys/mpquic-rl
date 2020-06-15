# from __future__ import print_function

import collections

XP_TYPE = "xpType"
CLIENT_PCAP = "clientPcap"
SERVER_PCAP = "serverPcap"
SNAPLEN_PCAP = "snaplenPcap"
SCHEDULER = "sched"
SCHEDULER_CLIENT = "schedc"
SCHEDULER_SERVER = "scheds"
CC = "congctrl"
KERNEL_PATH_MANAGER_CLIENT = "kpmc"
KERNEL_PATH_MANAGER_SERVER = "kpms"
RMEM = "rmem"
WMEM = "wmem"
AUTOCORK = "autocork"
EARLY_RETRANS = "earlyRetrans"

""" XP TYPES """
HTTPS = "https"
QUIC = "quic"
QUICREQRES = "quicreqres"

""" Specific to https """
HTTPS_FILE = "file"
DEPENDENCY_1 = "dependency_1"
DEPENDENCY_2 = "dependency_2"
DEPENDENCY_3 = "dependency_3"
DEPENDENCY_4 = "dependency_4"
DEPENDENCY_5 = "dependency_5"
HTTPS_RANDOM_SIZE = "file_size"
HTTPS_RANDOM_SIZE2 = "file_size2"
HTTPS_RANDOM_SIZE3 = "file_size3"
HTTPS_RANDOM_SIZE4 = "file_size4"
HTTPS_RANDOM_SIZE5 = "file_size5"

SINGLE_FILE = 'single_file'

""" Quic project """
PROJECT = "project"
WEB_BROWSE = "web_browse"
JSON_FILE = "json_file"
PATH_SCHEDULER = "path_scheduler"
BROWSER = "browser"
MULTIFILE = "multifile"
PRIORITY_LOW = "priority_low"
PRIORITY_HIGH = "priority_high"
PRIORITY_3 = "priority_3"
PRIORITY_4 = "priority_4"
PRIORITY_5 = "priority_5"


""" Specific to all QUIC experiences """
QUIC_MULTIPATH = "quicMultipath"

""" Specific to QUIC reqres experiences """
QUICREQRES_RUN_TIME = "quicReqresRunTime"

""" Default values """
DEFAULT_XP_TYPE = HTTPS
DEFAULT_CLIENT_PCAP = "yes"
DEFAULT_SERVER_PCAP = "no"
DEFAULT_SNAPLEN_PCAP = "100"
DEFAULT_SCHEDULER = "default"
DEFAULT_CC = "olia"
DEFAULT_KERNEL_PATH_MANAGER_CLIENT = "fullmesh"
DEFAULT_KERNEL_PATH_MANAGER_SERVER = "fullmesh"
DEFAULT_EARLY_RETRANS = "3"

""" Default values for specific fields to https """
DEFAULT_HTTPS_FILE = "random"
DEFAULT_HTTPS_RANDOM_SIZE = "1024"
DEFAULT_HTTPS_RANDOM_SIZE2 = "1024"
DEFAULT_HTTPS_RANDOM_SIZE3 = "1024"
DEFAULT_HTTPS_RANDOM_SIZE4 = "1024"
DEFAULT_HTTPS_RANDOM_SIZE5 = "1024"

DEFAULT_DEPENDENCY_1 = "0"
DEFAULT_DEPENDENCY_2 = "0"
DEFAULT_DEPENDENCY_3 = "0"
DEFAULT_DEPENDENCY_4 = "0"
DEFAULT_DEPENDENCY_5 = "0"

DEFAULT_SINGLE_FILE = "0"

""" Default quic project setting"""
DEFAULT_PROJECT = "quic-go"
DEFAULT_WEB_BROWSE = "0"
DEFAULT_JSON_FILE = "360.cn_"
DEFAULT_PATH_SCHEDULER = "MultiPath"
DEFAULT_BROWSER = "Safari"
DEFAULT_MULTIFILE = "0"
DEFAULT_PRIORITY_LOW = "20"
DEFAULT_PRIORITY_HIGH = "100"
DEFAULT_PRIORITY_3 = "50"
DEFAULT_PRIORITY_4 = "50"
DEFAULT_PRIORITY_5 = "50"


""" Default values for specific fields to all QUIC experiences """
DEFAULT_QUIC_MULTIPATH = "0"

""" Default values for specific fields to QUIC siri """
DEFAULT_QUICREQRES_RUN_TIME = "30"


def fillHttpsInfo(xpFile, xpDict):
    print(HTTPS_FILE + ":" + str(xpDict.get(HTTPS_FILE, DEFAULT_HTTPS_FILE)), file=xpFile)
    print(HTTPS_RANDOM_SIZE + ":" + str(xpDict.get(HTTPS_RANDOM_SIZE, DEFAULT_HTTPS_RANDOM_SIZE)), file=xpFile)
    print(HTTPS_RANDOM_SIZE2 + ":" + str(xpDict.get(HTTPS_RANDOM_SIZE2, DEFAULT_HTTPS_RANDOM_SIZE2)), file=xpFile)
    print(HTTPS_RANDOM_SIZE3 + ":" + str(xpDict.get(HTTPS_RANDOM_SIZE3, DEFAULT_HTTPS_RANDOM_SIZE3)), file=xpFile)
    print(HTTPS_RANDOM_SIZE4 + ":" + str(xpDict.get(HTTPS_RANDOM_SIZE4, DEFAULT_HTTPS_RANDOM_SIZE4)), file=xpFile)
    print(HTTPS_RANDOM_SIZE5 + ":" + str(xpDict.get(HTTPS_RANDOM_SIZE5, DEFAULT_HTTPS_RANDOM_SIZE5)), file=xpFile)


def fillCommonQUICInfo(xpFile, xpDict):
    print(QUIC_MULTIPATH + ":" + str(xpDict.get(QUIC_MULTIPATH, DEFAULT_QUIC_MULTIPATH)), file=xpFile)


def fillQUICInfo(xpFile, xpDict):
    fillCommonQUICInfo(xpFile, xpDict)
    print(HTTPS_FILE + ":" + str(xpDict.get(HTTPS_FILE, DEFAULT_HTTPS_FILE)), file=xpFile)
    print(HTTPS_RANDOM_SIZE + ":" + str(xpDict.get(HTTPS_RANDOM_SIZE, DEFAULT_HTTPS_RANDOM_SIZE)), file=xpFile)
    print(HTTPS_RANDOM_SIZE2 + ":" + str(xpDict.get(HTTPS_RANDOM_SIZE2, DEFAULT_HTTPS_RANDOM_SIZE2)), file=xpFile)
    print(HTTPS_RANDOM_SIZE3 + ":" + str(xpDict.get(HTTPS_RANDOM_SIZE3, DEFAULT_HTTPS_RANDOM_SIZE3)), file=xpFile)
    print(HTTPS_RANDOM_SIZE4 + ":" + str(xpDict.get(HTTPS_RANDOM_SIZE4, DEFAULT_HTTPS_RANDOM_SIZE4)), file=xpFile)
    print(HTTPS_RANDOM_SIZE5 + ":" + str(xpDict.get(HTTPS_RANDOM_SIZE5, DEFAULT_HTTPS_RANDOM_SIZE5)), file=xpFile)
    print(PROJECT + ":" +  str(xpDict.get(PROJECT, DEFAULT_PROJECT)), file=xpFile)
    print(WEB_BROWSE + ":" + str(xpDict.get(WEB_BROWSE,DEFAULT_WEB_BROWSE)),file=xpFile)
    print(JSON_FILE + ":" + str(xpDict.get(JSON_FILE,DEFAULT_JSON_FILE)),file=xpFile)
    print(PATH_SCHEDULER + ":" +str(xpDict.get(PATH_SCHEDULER,DEFAULT_PATH_SCHEDULER)),file=xpFile)
    print(BROWSER + ":" +str(xpDict.get(BROWSER,DEFAULT_BROWSER)),file=xpFile)
    print(SINGLE_FILE + ":" + str(xpDict.get(SINGLE_FILE,DEFAULT_SINGLE_FILE)),file=xpFile)
    print(MULTIFILE + ":" +  str(xpDict.get(MULTIFILE, DEFAULT_MULTIFILE)), file=xpFile)
    print(PRIORITY_HIGH + ":" +  str(xpDict.get(PRIORITY_HIGH, DEFAULT_PRIORITY_HIGH)), file=xpFile)
    print(PRIORITY_LOW + ":" +  str(xpDict.get(PRIORITY_LOW, DEFAULT_PRIORITY_LOW)), file=xpFile)
    print(PRIORITY_3 + ":" +  str(xpDict.get(PRIORITY_3, DEFAULT_PRIORITY_3)), file=xpFile)
    print(PRIORITY_4 + ":" +  str(xpDict.get(PRIORITY_4, DEFAULT_PRIORITY_4)), file=xpFile)
    print(PRIORITY_5 + ":" +  str(xpDict.get(PRIORITY_5, DEFAULT_PRIORITY_5)), file=xpFile)
    print(DEPENDENCY_1+":" + str(xpDict.get(DEPENDENCY_1,DEFAULT_DEPENDENCY_1)),file=xpFile)
    print(DEPENDENCY_2+":" + str(xpDict.get(DEPENDENCY_2,DEFAULT_DEPENDENCY_2)),file=xpFile)
    print(DEPENDENCY_3+":" + str(xpDict.get(DEPENDENCY_3,DEFAULT_DEPENDENCY_3)),file=xpFile)
    print(DEPENDENCY_4+":" + str(xpDict.get(DEPENDENCY_4,DEFAULT_DEPENDENCY_4)),file=xpFile)
    print(DEPENDENCY_5+":" + str(xpDict.get(DEPENDENCY_5,DEFAULT_DEPENDENCY_5)),file=xpFile)


def fillQUICReqresInfo(xpFile, xpDict):
    fillCommonQUICInfo(xpFile, xpDict)
    print(QUICREQRES_RUN_TIME + ":" + str(xpDict.get(QUICREQRES_RUN_TIME, DEFAULT_QUICREQRES_RUN_TIME)), file=xpFile)


def generateXpFile(xpFilename, xpDict):
    xpFile = open(xpFilename, 'w')
    xpType = xpDict.get(XP_TYPE, DEFAULT_XP_TYPE)
    """ First set common information for any experience """
    print(XP_TYPE + ":" + xpType, file=xpFile)
    print(CLIENT_PCAP + ":" + xpDict.get(CLIENT_PCAP, DEFAULT_CLIENT_PCAP), file=xpFile)
    print(SERVER_PCAP + ":" + xpDict.get(SERVER_PCAP, DEFAULT_SERVER_PCAP), file=xpFile)
    print(SNAPLEN_PCAP + ":" + xpDict.get(SNAPLEN_PCAP, DEFAULT_SNAPLEN_PCAP), file=xpFile)
    if SCHEDULER_CLIENT in xpDict and SCHEDULER_SERVER in xpDict:
        print(SCHEDULER_CLIENT + ":" + str(xpDict[SCHEDULER_CLIENT]), file=xpFile)
        print(SCHEDULER_SERVER + ":" + str(xpDict[SCHEDULER_SERVER]), file=xpFile)
    else:
        print(SCHEDULER + ":" + xpDict.get(SCHEDULER, DEFAULT_SCHEDULER), file=xpFile)
    print(CC + ":" + xpDict.get(CC, DEFAULT_CC), file=xpFile)
    print(KERNEL_PATH_MANAGER_CLIENT + ":" + xpDict.get(KERNEL_PATH_MANAGER_CLIENT, DEFAULT_KERNEL_PATH_MANAGER_CLIENT), file=xpFile)
    print(KERNEL_PATH_MANAGER_SERVER + ":" + xpDict.get(KERNEL_PATH_MANAGER_SERVER, DEFAULT_KERNEL_PATH_MANAGER_SERVER), file=xpFile)
    print(EARLY_RETRANS + ":" + str(xpDict.get(EARLY_RETRANS, DEFAULT_EARLY_RETRANS)), file=xpFile)
    """ Set rmem if defined (assume as string, int or iterable) """
    if RMEM in xpDict:
        rmemRaw = xpDict[RMEM]
        if isinstance(rmemRaw, int):
            rmem = (rmemRaw, rmemRaw, rmemRaw)
        elif isinstance(rmemRaw, str) or (isinstance(rmemRaw, collections.Iterable) and len(rmemRaw) == 3):
            # Assume it's ok
            rmem = rmemRaw
        else:
            raise Exception("Formatting error for rmem: " + str(rmemRaw))

        print(RMEM + ":" + str(rmem[0]), str(rmem[1]), str(rmem[2]), file=xpFile)

    if xpType == HTTPS:
        fillHttpsInfo(xpFile, xpDict)
    elif xpType == QUIC:
        fillQUICInfo(xpFile, xpDict)
    elif xpType == QUICREQRES:
        fillQUICReqresInfo(xpFile, xpDict)
    else:
        raise NotImplementedError("Experience not yet implemented: " + xpType)

    xpFile.close()


if __name__ == '__main__':
    xpHttpsDict = {
        XP_TYPE: HTTPS,
        HTTPS_RANDOM_SIZE: "2048",
        HTTPS_RANDOM_SIZE2: "2048",
        HTTPS_RANDOM_SIZE3: "2048",
        HTTPS_RANDOM_SIZE4: "2048",
        HTTPS_RANDOM_SIZE5: "2048"

    }
    generateXpFile("my_https_xp", xpHttpsDict)
