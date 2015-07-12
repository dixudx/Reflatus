from retflatus.loader import Loader
from retflatus.myjenkins import JenkinsManager
from retflatus.events import ZMQListener
import ConfigParser
from time import sleep
import threading


class Runner(threading.Thread):
    """
    backend runner class
    """
    def __init__(self, config):
        """
        @param config: the config file
        """
        threading.Thread.__init__(self, name="backend-runner")
        self.config = self._readConfig(config)
        self.flows, self.flow_map = self._getFlows()
        self.jenkinsmgr = self._getJenkinsMgr()
        self.zmq = self._getZMQ()
        self._stopped = False

    def _readConfig(self, filename):
        config = ConfigParser.ConfigParser()
        config.read(filename)
        return config

    def _getFlows(self):
        try:
            flow_config = self.config.get("flows", "config")
        except:
            flow_config = "./conf/flows.yaml"
        return Loader(flow_config).getConfig()

    def _getJenkinsMgr(self):
        url = self.config.get("jenkins", "url")
        user = self.config.get("jenkins", "user")
        password = self.config.get("jenkins", "password")
        return JenkinsManager(url, user, password)

    def _getZMQ(self):
        name = self.config.get("zmq", "name")
        addr = self.config.get("zmq", "addr")
        return ZMQListener(name,
                           addr,
                           self.jenkinsmgr,
                           self.flows)

    def run(self):
        self.zmq.start()
        while True:
            sleep(5)


if __name__ == "__main__":
    from retflatus.utils import setup_logging
    setup_logging()
    test_config = "./conf/config.conf"
    rc = Runner(test_config)
    rc.run()
