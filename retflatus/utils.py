import logging


class StoppedException(Exception):
    pass


class DuplicatedException(Exception):
    pass


def setup_logging():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(name)s: '
                               '(%(threadName)-10s) %(message)s')


class ConfigInfo(object):
    def getattr(self, attr):
        try:
            return self.__getattribute__(attr)
        except:
            return None
