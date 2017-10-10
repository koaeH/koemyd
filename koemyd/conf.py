# vi:ts=4:sw=4:syn=python

import re
import string
import socket

import koemyd.util
import koemyd.const
import koemyd.logger

import lib.kconf as kcp

class Settings(object):
    def __init__(self, kconf_file_path=koemyd.const.SETTINGS_PROGRAM_CONFIG_FILE):
        try:
            self.__kconf = kcp.KConfigParser(kconf_file_path)
        except kcp.KConfigParserError as e:
            koemyd.logger.crit("config", "%s:%s" % (kconf_file_path,e.message))
        except EnvironmentError as e:
            koemyd.logger.crit("config", "%s:could not read" % kconf_file_path)

        if not self.__kconf:
            self.__kconf["daemon"] = {
                "listen_addr": koemyd.const.SETTINGS_DEFAULT_LISTEN_ADDR,
                "listen_port": koemyd.const.SETTINGS_DEFAULT_LISTEN_PORT,
            }

            koemyd.logger.info("config", "%s:writing default kconf settings" % kconf_file_path)

            try: self.__kconf.save()
            except EnvironmentError:
                koemyd.logger.warn("config", "%s:could not write kconf file" % kconf_file_path)

        self.__listen_addr = str(koemyd.const.SETTINGS_DEFAULT_LISTEN_ADDR)
        self.__listen_port = int(koemyd.const.SETTINGS_DEFAULT_LISTEN_PORT)

        try:
            self.__setup()
        except kcp.KConfigParserError as e:
            koemyd.logger.crit("config", e)

    def __setup(self):
        self.listen_addr = self.__kconf["daemon"]["listen_addr"]
        self.listen_port = self.__kconf["daemon"]["listen_port"]

    @property
    def listen_addr(self): return self.__listen_addr

    @listen_addr.setter
    def listen_addr(self, value):
        if value:
            try:
                self.__listen_addr = socket.inet_ntoa(socket.inet_aton(value))
            except socket.error:
                koemyd.logger.warn("config", "daemon:listen_addr:%s is a not a valid ip address" % value)
        else:
            raise kcp.MissingOptionError("%s:missing option value" % "listen_addr")

    @property
    def listen_port(self): return self.__listen_port

    @listen_port.setter
    def listen_port(self, value):
        if value:
            if value.isdigit():
                value = int(value)
                if 0 <= value <= 65535:
                    self.__listen_port = value

                    if 1024 > value > 0:
                        koemyd.logger.warn("config", "daemon:listen_port:%d:administrative privileges required" % value)
                elif value > 65535:
                    koemyd.logger.crit("config", "daemon:listen_port:%d:not a valid port number" % value)
            else:
                koemyd.logger.crit("config", "daemon:listen_port:%s:non-numeric value" % value)
        else:
            raise kcp.MissingOptionError("%s:missing option value" % "listen_port")

    @property
    def listen_address(self): return (self.__listen_addr, self.__listen_port)

settings = Settings()
