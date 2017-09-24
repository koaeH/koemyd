# vi:ts=4:sw=4:syn=python

import os
import sys

import logging

import koemyd.const

logging.DATA = logging.DEBUG

logging.OOPS = logging.ERROR
logging.WARN = logging.WARNING
logging.CRIT = logging.CRITICAL

class Logger(object):
    def __init__(self):
        self.logger = logging.getLogger(koemyd.const.PROGRAM_NAME)
        self.format = logging.Formatter("[%(asctime)s] %(message)s", "%H:%M:%S")
        self.handle = logging.StreamHandler(sys.stdout)
        self.handle.setFormatter(self.format)
        self.logger.addHandler(self.handle)

        if koemyd.const.DATA_DEBUGGING: self.logger.setLevel(logging.DATA)
        else:
            self.logger.setLevel(logging.INFO)

    def __out(self, l, m):
        if self.logger.handlers: self.logger.log(l, m)
        else:
            sys.stderr.write(m + os.linesep)

    def data(self, module, message):
        self.__out(logging.DATA, "data:%s:%s" % (module, message))

    def info(self, module, message):
        self.__out(logging.INFO, "info:%s:%s" % (module, message))

    def warn(self, module, message):
        self.__out(logging.OOPS, "warn:%s:%s" % (module, message))

    def oops(self, module, message):
        self.__out(logging.OOPS, "oops:%s:%s" % (module, message))

    def crit(self, module, message, ex_code):
        self.__out(logging.CRIT, "crit:%s:%s" % (module, message))

        sys.exit(ex_code)

def data(module, message): logger.data(module, message)
def info(module, message): logger.info(module, message)
def warn(module, message): logger.warn(module, message)
def oops(module, message): logger.oops(module, message)
def crit(module, message): logger.crit(module, message, ex_code=1)

logger = Logger()
