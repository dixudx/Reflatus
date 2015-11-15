from reflatus.loader import Loader
from reflatus.myjenkins import JenkinsManager
from reflatus.events import ZMQListener
from exceptions import KeyError, AttributeError
import ConfigParser
import threading
import logging


class ServerInfo(object):

    def __init__(self, name, url, description, flow_maps):
        self.name = name
        self.url = self.validate_url(url)
        self.description = description
        self.flow_maps = flow_maps

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__,
                            self.name)

    @classmethod
    def validate_url(cls, url):
        """Strip and trailing slash to validate a url

        :param url: the url address
        :return: the valid url address
        :rtype: string
        """

        if url is None:
            return None

        url = url.strip()
        while url.endswith('/'):
            url = url[:-1]
        return url


class Runner(threading.Thread):
    """
    An Wrapped Class for Back-End Process
    """

    log = logging.getLogger('runner.Runner')

    def __init__(self, filepath):
        """
        @param filepath: the configuration file path
        """
        threading.Thread.__init__(self, name="backend-runner")
        self.filepath = filepath
        self.zmqs = list()
        self.servers_info = dict()
        self.config = self._readConfig()
        self._handleConfig()

    def _readConfig(self):
        self.log.info("Read configuration file: %s", self.filepath)
        config = ConfigParser.ConfigParser()
        config.read(self.filepath)
        return config

    def _handleConfig(self):
        self.log.debug("Start parsing configuration file: %s", self.filepath)
        servers = self.config.get("jenkins", "servers")
        if not servers:
            raise KeyError("No Jenkins Servers are specified")

        servers = servers.split(",")
        servers = self._strip_spaces(servers)
        for server in servers:
            sectname = "jenkins_%s" % server
            server_name = self.config.get(sectname, "name")

            server_description = self.config.get(sectname, "description")
            if not server_description:
                server_description = "No Description for %s" % server_name

            server_url = self.config.get(sectname, "url")
            if not server_url:
                raise AttributeError("Jenkins %s's url is empty" % server_url)

            server_user = self.config.get(sectname, "username")
            server_pw = self.config.get(sectname, "password")
            jenkins_mgr = JenkinsManager(server_url,
                                         server_user,
                                         server_pw)

            server_zmq_addr = self.config.get(sectname, "zmq_addr")
            server_flow_conf = self.config.get(sectname, "flows")
            self.log.debug("Start parsing Jenkins %s's flow configuration",
                           server_name)
            server_flows, server_flow_maps = self._getFlows(server_flow_conf)

            server_info = ServerInfo(server_name,
                                     server_url,
                                     server_description,
                                     server_flow_maps)
            self.servers_info[server_name] = server_info

            self.log.debug("Start registering %s to ZMQListener",
                           server_zmq_addr)
            server_zmq = ZMQListener("zmq_%s" % server_name,
                                     server_zmq_addr,
                                     jenkins_mgr,
                                     server_flows)
            self.zmqs.append(server_zmq)

    def _getFlows(self, flow_conf):
        if not flow_conf:
            raise AttributeError("No flow configuration file is specified ")

        confs = flow_conf.split(",")
        confs = self._strip_spaces(confs)
        reshaped_flows = dict()
        flow_maps = dict()
        for conf in confs:
            sectname = "flows_%s" % conf
            conf_file = self.config.get(sectname, "file")
            reshaped_flow, flow_map = Loader(conf_file).getConfig()
            reshaped_flows.update(reshaped_flow)
            flow_maps.update(flow_map)
        return reshaped_flows, flow_maps

    @classmethod
    def _strip_spaces(cls, alist):
        return map(lambda x: x.strip(), alist)

    def run(self):
        for zmq in self.zmqs:
            try:
                zmq.start()
            except:
                self.log.error("Unable to listen %s on %s",
                               zmq.name,
                               zmq.addr)


if __name__ == "__main__":
    from reflatus.utils import setup_logging
    setup_logging()
    test_config = "./new_config.conf"
    rc = Runner(test_config)
    rc.start()
