# vi:ts=4:sw=4:syn=python

import re
import string
import socket

import koemyd.util
import koemyd.const
import koemyd.logger

import ConfigParser as cp

class Settings(object):
    def __init__(self, settings_file=koemyd.const.SETTINGS_PROGRAM_CONFIG_FILE):
        self.__parser = cp.RawConfigParser()

        try:
            self.__parser.read(settings_file)
        except cp.MissingSectionHeaderError as e:
            koemyd.logger.crit("config", "%s:option(s) before [an empty] section" % settings_file)
        except cp.ParsingError as e:
            for n, _ in e.errors:
                koemyd.logger.warn("config", "%s:%d:syntax error" % (settings_file, long(n)))

            koemyd.logger.crit("config", "%s:parsing error!" % settings_file)

        if not self.__parser.sections():
            self.__parser.add_section("daemon")
            self.__parser.set("daemon", "listen_addr", koemyd.const.SETTINGS_DEFAULT_LISTEN_ADDR)
            self.__parser.set("daemon", "listen_port", koemyd.const.SETTINGS_DEFAULT_LISTEN_PORT)

            koemyd.logger.info("config", "%s:writing default configuration file" % settings_file)

            try:
                with open(settings_file, 'w') as f:
                    self.__parser.write(f)
            except (OSError,IOError) as e:
                koemyd.logger.warn("config", "could not write settings into %s" % settings_file)

        self.__listen_addr = str(koemyd.const.SETTINGS_DEFAULT_LISTEN_ADDR)
        self.__listen_port = int(koemyd.const.SETTINGS_DEFAULT_LISTEN_PORT)

        self.__setup()

    def __setup(self):
        __s_white = lambda(s): re.sub(r"\s+", r" ", s).strip()
        __c_ascii = lambda(s): filter(lambda(c): c in string.printable, s)
        __t_ol_ov = lambda(s): __s_white(re.sub(r"(?s)\s.*$", r"", __c_ascii(s)))

        try:
            self.listen_addr = __t_ol_ov(self.__parser.get("daemon", "listen_addr"))
            self.listen_port = __t_ol_ov(self.__parser.get("daemon", "listen_port"))
        except cp.NoOptionError as e:
            koemyd.logger.crit("config", "%s:%s:missing option" % (e.section, e.option))
        except cp.NoSectionError,  e:
            koemyd.logger.crit("config", "%s:missing section"   % (e.section))

    @property
    def listen_addr(self): return self.__listen_addr

    @listen_addr.setter
    def listen_addr(self, value):
        if not value: raise cp.NoOptionError("listen_addr", "daemon")

        try:
            value = socket.inet_aton(value)
            self.__listen_addr = socket.inet_ntoa(value)
        except socket.error:
            koemyd.logger.warn("config", "daemon:listen_addr:%s is a not a valid ip address" % value)

    @property
    def listen_port(self): return self.__listen_port

    @listen_port.setter
    def listen_port(self, value):
        if not value: raise cp.NoOptionError("listen_port", "daemon")

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

    @property
    def listen_address(self): return (self.__listen_addr, self.__listen_port)

settings = Settings()
