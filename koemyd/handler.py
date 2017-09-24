# vi:ts=4:sw=4:syn=python

import os

import time
import thread
import threading
import traceback

import koemyd.util
import koemyd.const
import koemyd.struct
import koemyd.logger
import koemyd.fetching

class Handler(threading.Thread):
    def __init__(self, koemyd_connection_link):
        super(self.__class__, self).__init__()
        self.__link = koemyd_connection_link
        self.__request = None

    def __parse_client_request(self):
        line = self.__link.client.readline()
        while not line.strip(koemyd.const.CRLF):
            line = self.__link.client.readline()

        self.__request = koemyd.fetching.ClientRequest(line)

        line = self.__link.client.readline()
        while line.strip(koemyd.const.CRLF):
            k, v = self.__request.headers.parse(line)
            line = self.__link.client.readline()
            self.__request.headers[k] = v

        if not self.__request.is_tunneling:
            koemyd.logger.info("c#%s" % self.__link.uuid, "s#%s:requested procuration to %s" % (
                self.__link.client.uuid, self.__request,
            ))
        else:
            koemyd.logger.info("c#%s" % self.__link.uuid, "s#%s:requested tunnel procuration to %s:%d" % (
                self.__link.client.uuid, self.__request.host, self.__request.port,
            ))

    def __setup_server_connect(self):
        self.__link.server.connect(self.__request.address)

        if self.__request.is_tunneling:
            self.__link.client.tx(koemyd.const.HTTP_CRLF.join([
                "HTTP/1.1 200 Connection established",
                "Proxy-Agent: %s/%s" % (
                    koemyd.const.PROGRAM_NAME,
                    koemyd.const.VERSION
                ),
                koemyd.const.HTTP_CRLF
            ]))

    def __relay_server_request(self):
        request = koemyd.fetching.ServerRequest(self.__request.method, self.__request.path)
        for k, v in self.__request.headers.iteritems():
            if k.lower() not in map(str.lower, koemyd.const.HTTP_HEADERS_SKIP_TO_SERVER):
                request.headers[k] = v

        request.headers["Host"] = self.__request.host
        if not self.__request.port == 80: 
            request.headers["Host"] += ":%d" % self.__request.port

        request.headers["Connection"] = "keep-alive"

        self.__link.server.tx(request.line)
        self.__link.server.tx(koemyd.const.CRLF)
        for k, v in request.headers.iteritems():
            self.__link.server.tx("%s: %s" % (k, v))
            self.__link.server.tx(koemyd.const.CRLF)

        self.__link.server.tx(koemyd.const.CRLF)

        if "Content-Length" in self.__request.headers:
            self.__link.relay(
                long(self.__request.headers["Content-Length"]),
                perms=[self.__link.RELAY_PERM_C_RX_S_TX]
            )

    def __relay_server_reply(self):
        response = koemyd.fetching.ServerResponse(self.__link.server.readline())
        line = self.__link.server.readline()
        while line.strip(koemyd.const.CRLF):
            try:
                k, v = response.headers.parse(line)
                response.headers[k] = v
            except koemyd.struct.HTTPHeaderError as e:
                e.code = 502
                raise e

            line = self.__link.server.readline()

        koemyd.logger.info("c#%s" % self.__link.uuid, "s#%s:p#%s:%d:r#%d:response:%s" % (
                    self.__link.server.uuid, self.__request.host,
                    self.__request.port, response.code,
                    response.reason.lower()
                )
            )

        if response.is_tainted:
            self.__link.server.is_tainted = True

            koemyd.logger.info("c#%s" % self.__link.uuid,
                "s#%s:p#%s:%d:r#%d:tainted!" % (
                    self.__link.server.uuid, self.__request.host,
                    self.__request.port, response.code,
                )
            )

        if self.__request.is_persistent:
            response.headers["Connection"] = "keep-alive"
        else:
            response.headers["Connection"] = "close"

        encoder = response.encoder

        self.__link.client.tx(response.line)
        self.__link.client.tx(koemyd.const.CRLF)
        for k, v in response.headers.iteritems():
            if k.lower() not in map(str.lower, koemyd.const.HTTP_HEADERS_SKIP_TO_CLIENT):
                self.__link.client.tx("%s: %s" % (k, v))
                self.__link.client.tx(koemyd.const.CRLF)

        self.__link.client.tx(koemyd.const.CRLF)

        if response.expect_body:
            if encoder: self.__link.relay_encoded(encoder)
            else:
                self.__link.relay(
                    long(response.headers["Content-Length"]),
                    perms=[
                        self.__link.RELAY_PERM_S_RX_C_TX
                    ]
                )

    def __handle(self):
        try:
            self.__parse_client_request()
            self.__setup_server_connect()

            if self.__request.is_tunneling: self.__link.relay()
            else:
                self.__relay_server_request()
                self.__relay_server_reply()

                if self.__request.is_persistent:
                   if self.__link.server.is_tainted:
                      self.__link.server.reset()
                   self.__handle()
        except koemyd.struct.HTTPError, e:
            self.__link.error(e.code, e.line)
        except koemyd.fetching.ConnectionTimeoutError as e:
            self.__link.error(504, e.message)
        except koemyd.fetching.ConnectionError as e:
            self.__link.error(502, e.message)
        except Exception as exc: # fallback
            s = traceback.format_exc()
            self.__link.error(500, s)
        except KeyboardInterrupt:
            thread.interrupt_main()
        finally:
            self.__link.close()

    def run(self):
        self.__handle()
