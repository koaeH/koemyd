# vi:ts=4:sw=4:syn=python

import sys

import socket
import thread
import threading

import koemyd.conf
import koemyd.const
import koemyd.logger
import koemyd.handler
import koemyd.fetching

class Server(object):
    def __init__(self):
        self.__sock   = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def __serve_forever(self):
        try:
            while True:
                client_sock, client_address = self.__sock.accept()
                if threading.active_count() <= koemyd.const.DAEMON_MAX_CONCURRENCY:
                    try:
                        link = koemyd.fetching.Connection(client_sock)
                        handler = koemyd.handler.Handler(link)
                        handler.daemon = True
                        handler.start()
                    except thread.error:
                        koemyd.logger.oops("daemon", "exception caught when creating new thread")
                        client_sock.shutdown(socket.SHUT_RDWR)
                        client_sock.close()
                else:
                    koemyd.logger.warn("daemon", "maximum number of clients exceeded")
                    client_sock.shutdown(socket.SHUT_RDWR)
                    client_sock.close()
        except KeyboardInterrupt:
            sys.stderr.write(koemyd.const.HTTP_CRLF)
            self.__sock.shutdown(socket.SHUT_RDWR)
            self.__sock.close()
        except socket.error:
            pass

    def start(self):
        koemyd.logger.info("daemon", "%s:%s" % (koemyd.const.PROGRAM_NAME, koemyd.const.PROGRAM_DESC))

        try:
            self.__sock.bind(koemyd.conf.settings.listen_address)
            self.__sock.listen(max(128, socket.SOMAXCONN))
            self.address = self.__sock.getsockname()
        except socket.error as (_, m):
            koemyd.logger.crit("daemon", "could not bind to %(addr)s:%(port)d (%(desc)s)" % {
                "addr" : koemyd.conf.settings.listen_addr,
                "port" : koemyd.conf.settings.listen_port,
                "desc" : m.lower()
            })

        koemyd.logger.info("daemon", "proxy is now listening on http://%s:%d" % self.address)

        self.__serve_forever()
