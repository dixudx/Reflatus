from flask import Flask
from retflatus.runner import Runner


class Retflatus(Flask):
    """
    a wrapped class to host flask app and backend runner
    Inherit from Flask and Initialize Runner in __init__
    """
    def __init__(self, import_name, beconfig="./conf/config.conf",
                 static_path=None, static_url_path=None,
                 static_folder='static', template_folder='templates',
                 instance_path=None, instance_relative_config=False):
        """
        :param beconfig: back-end config (used for Runner)
        other params are inherited from flask
        """
        super(Retflatus, self).__init__(import_name, static_path=static_path,
                                        static_url_path=static_url_path,
                                        static_folder=static_folder,
                                        template_folder=template_folder,
                                        instance_path=instance_path,
                                        instance_relative_config=instance_relative_config)
        self.beconfig = beconfig
        self._startRunner()
        self.flow_map = self.runner.flow_map

    def _startRunner(self):
        self.runner = Runner(self.beconfig)
        self.runner.start()
