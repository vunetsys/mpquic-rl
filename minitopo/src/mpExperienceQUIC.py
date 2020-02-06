from mpExperience import MpExperience
from mpParamXp import MpParamXp
import os


class MpExperienceQUIC(MpExperience):
    GO_BIN = "/usr/local/go/bin/go"
    SERVER_LOG = "quic_server.log"
    CLIENT_LOG = "quic_client.log"
    # CLIENT_GO_FILE = "~/go/src/github.com/lucas-clemente/quic-go/example/client_benchmarker/main.go"
    # SERVER_GO_FILE = "~/go/src/github.com/lucas-clemente/quic-go/example/main.go"
    # CERTPATH = "~/go/src/github.com/lucas-clemente/quic-go/example/"

    PING_OUTPUT = "ping.log"

    def __init__(self, xpParamFile, mpTopo, mpConfig):
        MpExperience.__init__(self, xpParamFile, mpTopo, mpConfig)
        self.loadParam()
        self.ping()
        MpExperience.classicRun(self)

    def ping(self):
        self.mpTopo.commandTo(self.mpConfig.client, "rm " + \
                              MpExperienceQUIC.PING_OUTPUT)
        count = self.xpParam.getParam(MpParamXp.PINGCOUNT)
        for i in range(0, self.mpConfig.getClientInterfaceCount()):
            cmd = self.pingCommand(self.mpConfig.getClientIP(i),
                                   self.mpConfig.getServerIP(), n=count)
            self.mpTopo.commandTo(self.mpConfig.client, cmd)

    def pingCommand(self, fromIP, toIP, n=5):
        s = "ping -c " + str(n) + " -I " + fromIP + " " + toIP + \
            " >> " + MpExperienceQUIC.PING_OUTPUT
        print(s)
        return s

    def loadParam(self):
        """
		todo : param LD_PRELOAD ??
		"""
        self.file = self.xpParam.getParam(MpParamXp.HTTPSFILE)
        self.dependency_1 = self.xpParam.getParam(MpParamXp.DEPENDENCY_1)
        self.dependency_2 = self.xpParam.getParam(MpParamXp.DEPENDENCY_2)
        self.dependency_3 = self.xpParam.getParam(MpParamXp.DEPENDENCY_3)
        self.dependency_4 = self.xpParam.getParam(MpParamXp.DEPENDENCY_4)
        self.dependency_5 = self.xpParam.getParam(MpParamXp.DEPENDENCY_5)
        self.random_size = self.xpParam.getParam(MpParamXp.HTTPSRANDOMSIZE)
        self.random_size2 = self.xpParam.getParam(MpParamXp.HTTPSRANDOMSIZE2)
        self.random_size3 = self.xpParam.getParam(MpParamXp.HTTPSRANDOMSIZE3)
        self.random_size4 = self.xpParam.getParam(MpParamXp.HTTPSRANDOMSIZE4)
        self.random_size5 = self.xpParam.getParam(MpParamXp.HTTPSRANDOMSIZE5)
        self.priority_low = self.xpParam.getParam(MpParamXp.PRIORITYLOW)
        self.priority_high = self.xpParam.getParam(MpParamXp.PRIORITYHIGH)
        self.priority_3 = self.xpParam.getParam(MpParamXp.PRIORITY3)
        self.priority_4 = self.xpParam.getParam(MpParamXp.PRIORITY4)
        self.priority_5 = self.xpParam.getParam(MpParamXp.PRIORITY5)

        self.project = self.xpParam.getParam(MpParamXp.PROJECT)
        self.web_browse = self.xpParam.getParam(MpParamXp.WEB_BROWSE)
        self.json_file = self.xpParam.getParam(MpParamXp.JSON_FILE)
        self.path_scheduler = self.xpParam.getParam(MpParamXp.PATH_SCHEDULER)
        self.browser = self.xpParam.getParam(MpParamXp.BROWSER)
        self.single_file = self.xpParam.getParam(MpParamXp.SINGLE_FILE)
        self.multifile = self.xpParam.getParam(MpParamXp.MULTIFILE)
        self.multipath = self.xpParam.getParam(MpParamXp.QUICMULTIPATH)
        if self.web_browse == "0":
            self.client_go_file = "~/go/src/github.com/lucas-clemente/" + self.project + "/example/client_benchmarker/main.go"
        else:
            self.client_go_file = "~/go/src/github.com/lucas-clemente/" + self.project + "/example/client_browse_deptree/main.go"
        self.server_go_file = "~/go/src/github.com/lucas-clemente/" + self.project + "/example/main.go"

        self.certpath = "~/go/src/github.com/lucas-clemente/" + self.project + "/example/"
        self.graphpath = "/dependency_graphs/"+self.json_file +"/"+self.json_file+".json" #relative path to root
        self.serverpath = "/home/mininet/go/src/github.com/lucas-clemente/server" #root path on server
        self.clientpath = "/home/mininet/go/src/github.com/lucas-clemente/client" #root path on server

    def prepare(self):
        MpExperience.prepare(self)
        self.mpTopo.commandTo(self.mpConfig.client, "rm " + \
                              MpExperienceQUIC.CLIENT_LOG)
        self.mpTopo.commandTo(self.mpConfig.server, "rm " + \
                              MpExperienceQUIC.SERVER_LOG)
        if self.file == "random":
            self.mpTopo.commandTo(self.mpConfig.client,
                                  "dd if=/dev/urandom of=random1 bs=1K count=" + \
                                  self.random_size)
            if self.single_file == "0":
                self.mpTopo.commandTo(self.mpConfig.client,
                                      "dd if=/dev/urandom of=random2 bs=1K count=" + \
                                      self.random_size2)
                if self.multifile == "1":
                    self.mpTopo.commandTo(self.mpConfig.client,
                                          "dd if=/dev/urandom of=random3 bs=1K count=" + \
                                          self.random_size3)
                    self.mpTopo.commandTo(self.mpConfig.client,
                                          "dd if=/dev/urandom of=random4 bs=1K count=" + \
                                          self.random_size4)
                    self.mpTopo.commandTo(self.mpConfig.client,
                                          "dd if=/dev/urandom of=random5 bs=1K count=" + \
                                          self.random_size5)
        # SHI: add random2

    def getQUICServerCmd(self):
        s = "./server_main "
        if self.web_browse == "1":
            if self.project == "quic-go":
                s += " -ps " + self.path_scheduler + " "
            s += " -www "+ self.serverpath + " -certpath " + self.certpath + " -bind 0.0.0.0:6121 &>"
        else:
            if self.project == "quic-go":
                s += " -ps " + self.path_scheduler + " "
            s += " -www . -certpath " + self.certpath + " -bind 0.0.0.0:6121 &>"
        s += MpExperienceQUIC.SERVER_LOG + " &"
        print(s)
        return s

    def getQUICClientCmd(self):
        s = "./main"
        if int(self.multipath) > 0:
            s += " -m -c "
        if self.web_browse == "0":
            # SHI: request two files (random1 and random2) in the same time
            if self.project == "quic-go":
                s += " -ps " + self.path_scheduler + " "
            s += " https://" + self.mpConfig.getServerIP() + ":6121/random1 "
            if self.project == "quic-go"  or self.project == "sa-ecf":
                s += self.priority_high
                s += " "
                s += self.dependency_1
            if self.single_file == "0":
                s += " https://" + self.mpConfig.getServerIP() + ":6121/random2 "
                if self.project == "quic-go"  or self.project == "sa-ecf":
                    s += self.priority_low
                    s += " "
                    s += self.dependency_2
                if  self.multifile == "1":
                    s += " https://" + self.mpConfig.getServerIP() + ":6121/random3 "
                    if self.project == "quic-go" or self.project == "sa-ecf":
                        s += self.priority_3
                        s += " "
                        s += self.dependency_3
                    s += " https://" + self.mpConfig.getServerIP() + ":6121/random4 "
                    if self.project == "quic-go" or self.project == "sa-ecf":
                        s += self.priority_4
                        s += " "
                        s += self.dependency_4
                    s += " https://" + self.mpConfig.getServerIP() + ":6121/random5 "
                    if self.project == "quic-go" or self.project == "sa-ecf":
                        s += self.priority_5
                        s += " "
                        s += self.dependency_5
        else:
            if 'deptree' in self.client_go_file:
                s += " -b " + self.browser + " "
            if self.project == "quic-go":
                s += " -ps " + self.path_scheduler + " "
            s += self.clientpath + self.graphpath  # specify local dependency graph path
        s += " &>" + MpExperienceQUIC.CLIENT_LOG
        print(s)
        return s

    def getQUICClientPreCmd(self):
        s = "./main"
        if int(self.multipath) > 0:
            s += " -m "
        s += " -c https://" + self.mpConfig.getServerIP() + ":6121/ugfiugizuegiugzeffg "
        if self.project == "quic-go"  or self.project == "sa-ecf":
            s += self.priority_high
            s += " 0 "
        s += " &> quic_client_pre.log"
        print(s)
        return s

    def compileGoFiles(self):
        cmd = MpExperienceQUIC.GO_BIN + " build " + self.server_go_file
        self.mpTopo.commandTo(self.mpConfig.server, cmd)
        self.mpTopo.commandTo(self.mpConfig.server, "mv main server_main")
        cmd = MpExperienceQUIC.GO_BIN + " build " + self.client_go_file
        self.mpTopo.commandTo(self.mpConfig.server, cmd)

    def clean(self):
        MpExperience.clean(self)
        if self.file == "random":
            self.mpTopo.commandTo(self.mpConfig.client, "rm random*")

    def run(self):
        self.compileGoFiles()
        cmd = self.getQUICServerCmd()
        self.mpTopo.commandTo(self.mpConfig.server, "netstat -sn > netstat_server_before")
        self.mpTopo.commandTo(self.mpConfig.server, cmd)

        self.mpTopo.commandTo(self.mpConfig.client, "sleep 2")

        self.mpTopo.commandTo(self.mpConfig.client, "netstat -sn > netstat_client_before")

        if self.web_browse == "0":
            cmd = self.getQUICClientPreCmd()
            self.mpTopo.commandTo(self.mpConfig.client, cmd)

        cmd = self.getQUICClientCmd()
        self.mpTopo.commandTo(self.mpConfig.client, cmd)
        self.mpTopo.commandTo(self.mpConfig.server, "netstat -sn > netstat_server_after")
        self.mpTopo.commandTo(self.mpConfig.client, "netstat -sn > netstat_client_after")

        self.mpTopo.commandTo(self.mpConfig.server, "pkill -f " + self.server_go_file)

        self.mpTopo.commandTo(self.mpConfig.client, "sleep 2")
        # Need to delete the go-build directory in tmp; could lead to no more space left error
        self.mpTopo.commandTo(self.mpConfig.client, "rm -r /tmp/go-build*")
        # Remove cache data
        self.mpTopo.commandTo(self.mpConfig.client, "rm cache_*")
