# vi:ts=4:sw=4:syn=python

import time
import errno
import socket
import select
import httplib
import urlparse

import koemyd.base
import koemyd.util
import koemyd.const
import koemyd.trans
import koemyd.struct
import koemyd.logger

class ClientRequest(koemyd.struct.HTTPRequest):
    def __init__(self, line=str()):
        super(ClientRequest, self).__init__(line)

        self.scheme = str() # e.g., http
        self.host   = str() # e.g., remote.test
        self.port   = int() # e.g., 80
        self.path   = str() # e.g., /

        self.__parse()

    def __parse(self):
        if not self.method == "CONNECT":
            parts = urlparse.urlparse(self.uri)
            if parts.scheme:
                self.scheme = parts.scheme
                if self.scheme in ["http"]:
                    self.host = parts.hostname
                    if not self.host:
                        raise ClientRequestError(400, "missing hostname in request URI")
                    self.port = int(parts.port or 80)
                    self.path = parts.path or '/'
                    if parts.query:
                        self.path += "?%s" % parts.query
                else:
                    raise ClientRequestError(400, "%s:unknown scheme" % parts.scheme)
            else:
                if parts.path.startswith('/'):
                    raise ClientRequestError(403, "%s:access denied" % parts.path)
                else:
                    raise ClientRequestError(400, "could not parse request")
        else:
            try:
                self.host, self.port = self.uri.split(':') # do not , 1)
            except ValueError:
                raise ClientRequestError(400, "CONNECT:bad address")

            self.host = self.host.lower()
            self.port = int(self.port)

    @property
    def is_tunneling(self): return "CONNECT" == self.method

    @property
    def address(self): return (self.host, self.port)

    @property
    def is_persistent(self):
        k_a = True if self.http_version.endswith("1.1") else False

        for k in ["Proxy-Connection", "Connection"]:
            if k in self.headers:
               if "keep-alive" == self.headers[k].lower(): k_a = 1
               if      "close" == self.headers[k].lower(): k_a = 0
               if             not self.headers[k].strip(): k_a = 0

        if self.is_tunneling: k_a = False

        return bool(k_a)

    def __str__(self): return self.uri # auth-form

class ClientRequestError(koemyd.struct.HTTPError): pass

class ServerRequest(koemyd.struct.HTTPRequest):
    def __init__(self, method, path, http_version="HTTP/1.1"):
        super(ServerRequest, self).__init__("%s %s %s" % (method, path, http_version))

class ServerResponse(koemyd.struct.HTTPResponse):
    def __init__(self, line):
        super(ServerResponse, self).__init__(line)

        self.__coder = None
        
    def __set_coder(self):
        if "Transfer-Encoding" in self.headers:
            h_t_e = self.headers["Transfer-Encoding"].lower()
            if h_t_e == "chunked":
                self.__coder = koemyd.trans.ChunkDecoder()
            else:
                raise ServerResponse(502, "%s:unsupported transfer-encoding")
        elif not "Content-Length" in self.headers:
            self.headers["Transfer-Encoding"] = "chunked"
            self.__coder = koemyd.trans.ChunkEncoder()

        return self.__coder

    @property
    def coder(self): return self.__coder if self.__coder else self.__set_coder()

    @property
    def is_tainted(self):
        i_t = int()

        if "Connection" in self.headers:
            if "keep-alive" == self.headers["Connection"].lower(): i_t = 0
            if      "close" == self.headers["Connection"].lower(): i_t = 1
            if             not self.headers["Connection"].strip(): i_t = 1
        else:
            i_t = 1

        return bool(i_t)

class Connection(koemyd.base.UUIDObject):
    RELAY_PERM_S_RX_C_TX = 0x118E0006
    RELAY_PERM_C_RX_S_TX = 0x7E440009

    def __init__(self, client_sock, server_sock=None):
        super(Connection, self).__init__()

        self.client = ConnectionSocket(self, client_sock)
        self.server = ConnectionSocket(self, server_sock)

    def relay(self, size=None, perms=[RELAY_PERM_S_RX_C_TX, RELAY_PERM_C_RX_S_TX]):
        bytes_sent_to_client = 0
        bytes_sent_to_server = 0

        time_last_op = time.time()
        self.client.setblocking(0)
        self.server.setblocking(0)
        while (time.time() - time_last_op) < koemyd.const.SOCKET_TIMEOUT:
            rsocks, wsocks, xsocks = [], [], []

            if self.RELAY_PERM_S_RX_C_TX in perms:
                if len(self.server.cache) < koemyd.const.SOCKET_BUFSIZE:
                    rsocks.append(self.server)
                if self.server.cache:
                    wsocks.append(self.client)

            if self.RELAY_PERM_C_RX_S_TX in perms:
                if len(self.client.cache) < koemyd.const.SOCKET_BUFSIZE:
                    rsocks.append(self.client)
                if self.client.cache:
                    wsocks.append(self.server)

            rx, tx, _ = select.select(rsocks, wsocks, xsocks, koemyd.const.SOCKET_TIMEOUT)

            if rx or tx: time_last_op = time.time()

            if rx:
                if self.server in rx:
                    data = self.server.rx(koemyd.const.SOCKET_BUFSIZE)
                    if data:
                        self.server.cache += data
                    else:
                        break

                if self.client in rx:
                    data = self.client.rx(koemyd.const.SOCKET_BUFSIZE)
                    if data:
                        self.client.cache += data
                    else:
                        break

            if tx:
                if self.server in tx:
                    if size:
                        bytes_queued =(size-bytes_sent_to_server)
                        if len(self.client.cache) > bytes_queued:
                            b = self.server.tx(self.client.cache[:bytes_queued])
                            self.client.cache = self.client.cache[bytes_queued:]
                        else:
                            b = self.server.tx(self.client.cache)
                            self.client.cache = bytearray()
                    else:
                        b = self.server.tx(self.client.cache)
                        self.client.cache = bytearray()

                    bytes_sent_to_server += b

                if size and bytes_sent_to_server >= size: break

                if self.client in tx:
                    if size:
                        bytes_queued =(size-bytes_sent_to_client)
                        if len(self.server.cache) > bytes_queued:
                            b = self.client.tx(self.server.cache[:bytes_queued])
                            self.server.cache = self.server.cache[bytes_queued:]
                        else:
                            b = self.client.tx(self.server.cache)
                            self.server.cache = bytearray()
                    else:
                        b = self.client.tx(self.server.cache)
                        self.server.cache = bytearray()

                    bytes_sent_to_client += b

                if size and bytes_sent_to_client >= size: break

        if bytes_sent_to_server:
            koemyd.logger.data("c#%s" % self.uuid,
                               "s#%s->s#%s:relay:stat:bytes_sent:%d" % (
                                    self.server.uuid, self.client.uuid,
                                    bytes_sent_to_server
                                ))

        if bytes_sent_to_client:
            koemyd.logger.data("c#%s" % self.uuid,
                               "s#%s->s#%s:relay:stat:bytes_sent:%d" % (
                                    self.client.uuid, self.server.uuid,
                                    bytes_sent_to_client
                                ))

    def relay_encoded(self, coder):
        self.server.setblocking(0)
        _time_last_op = time.time()
        while coder.keep_feeding:
            if (time.time() - _time_last_op) < koemyd.const.SOCKET_TIMEOUT:
                r, _, _ = select.select([self.server], [], [], koemyd.const.SOCKET_TIMEOUT)

                if self.server in r:
                    try: 
                         coder.feed(self.server.rx(koemyd.const.SOCKET_BUFSIZE))
                    except koemyd.trans.ChunksCodedException:
                        for c in coder.flush():
                            koemyd.logger.data("c#%s" % self.uuid,
                                               "s#%s->s#%s:relay_encoded:chunk(%s,%s)" % (
                                                  self.server.uuid, self.client.uuid,
                                                  "%X" % c.size, koemyd.util.dump(c.data) or "--"
                                               ))

                            self.client.tx(koemyd.const.HTTP_CRLF.join(["%X" % c.size, c.data]))
                            self.client.tx(koemyd.const.HTTP_CRLF)
            else:
                raise ConnectionTimeoutError("encoded:connection timeout")
        self.server.setblocking(1)

        self.client.tx(koemyd.const.HTTP_CRLF)

        self.server.cache += coder.cache

        if not self.server.is_tainted: 
            self.server.readline()

    def error(self, code, message=None, do_relay_http_error=True):
        code_description = httplib.responses[code]
        if not message: message = code_description

        koemyd.logger.oops("c#%s" % self.uuid, "e#%04d:%s" % (code, message.lower()))

        if do_relay_http_error:
            body  = code_description.title()
            body += koemyd.const.HTTP_CRLF * 2 + message.lower()
            body += koemyd.const.HTTP_CRLF * 2 + "! c#%s:e#%04d" % (self.uuid, code)

            try:
                self.client.setblocking(0)
                self.client.tx(koemyd.const.HTTP_CRLF.join([
                    "HTTP/1.1 %d %s" % (code, code_description),
                    "%s: %s" % ("Content-Type","text/plain"),
                    "%s: %d" % ("Content-Length", len(body)),
                    "%s: %s" % ("Connection", "close"),
                    koemyd.const.HTTP_CRLF
                ]) + body)
            except socket.error as e:
                pass

    def close(self):
        self.server.close()
        self.client.close()

class ConnectionError(Exception): pass

class ConnectionSocket(koemyd.base.UUIDObject):
    def __init__(self, link, __sock=None):
        self.__link = link
        self.setup(__sock)

        self.__peer_address = None
        try:
            self.__peer_address = self.__sock.getpeername()
            koemyd.logger.info("c#%s:s#%s" % (self.__link.uuid, self.uuid),
                               "p#%s:%d:connection established"
                               % self.__peer_address)
        except socket.error: pass

    def setup(self, sock=None):
        super(ConnectionSocket, self).__init__()
        self.__sock = sock if sock else socket.socket()
        self.__sock.settimeout(koemyd.const.SOCKET_TIMEOUT)
        self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.cache = bytearray()

        self.is_tainted = False

    def __getattr__(self, item): return getattr(self.__sock, item)

    def connect(self, address):
        koemyd.logger.info("c#%s:s#%s" % (self.__link.uuid, self.uuid), "p#%s:%d:connecting..." % address)

        if not address == self.__peer_address: self.reset()

        try:
            self.__sock.connect(address)
        except socket.timeout:
            raise ConnectionSocketError("%s:could not connect (connection timeout)" % ("p#%s:%d" % address))
        except socket.error as (e_n, m):
            if e_n not in [errno.EISCONN]:
                raise ConnectionSocketError("%s:could not connect (%s)" % ("p#%s:%d" % address, m))

        self.__peer_address = peer_address = self.__sock.getpeername()

        koemyd.logger.info("c#%s:s#%s" % (self.__link.uuid, self.uuid),
                           "p#%s:%d:connection established"
                           % self.__peer_address)

    def rx(self, size):
        d = bytearray()

        if self.cache:
            d += self.cache[:size]
            self.cache = bytearray()

            koemyd.logger.data("c#%s:s#%s" % (self.__link.uuid, self.uuid), "cr:%s" % koemyd.util.dump(d))

        if not koemyd.const.DATA_DEBUGGING:
            try:
                d += self.__sock.recv(size)
            except socket.error as e:
                if e.errno in [errno.ECONNRESET]:
                    pass
        else:
            while size > len(d):
                try:
                    c = self.__sock.recv(min(size - len(d), koemyd.const.SOCKET_BUFSIZE))
                    if c: d += c
                    else:
                        break

                    koemyd.logger.data("c#%s:s#%s" % (self.__link.uuid, self.uuid), "rx:%s" % koemyd.util.dump(c))
                except socket.error as e:
                    if e.errno in [errno.EAGAIN, errno.ECONNRESET]:
                        break

        return str(d)

    def tx(self, data):
        if not koemyd.const.DATA_DEBUGGING:
            try: return self.__sock.send(data)
            except socket.error as e:
                if e.errno in [ errno.EPIPE ]:
                    return 0

        bytes_sent = 0
        while bytes_sent < len(data):
            c = data[bytes_sent:bytes_sent + koemyd.const.SOCKET_BUFSIZE]

            try:
                bytes_sent += self.__sock.send(c)

                koemyd.logger.data("c#%s:s#%s" % (self.__link.uuid, self.uuid), "tx:%s" % koemyd.util.dump(c))
            except socket.error as e:
                if e.errno in [errno.EPIPE]:
                    pass

        return bytes_sent

    def readline(self, max_line_length=0x4000):
        d = bytearray()

        if self.cache:
            d += self.cache
            self.cache = bytearray()

            koemyd.logger.data("c#%s:s#%s" % (self.__link.uuid,self.uuid), "cr:%s" % koemyd.util.dump(d))

        self.__sock.setblocking(0)
        _last_access = time.time()
        while not '\n' in d and max_line_length > len(d):
            if (time.time() - _last_access) < koemyd.const.SOCKET_TIMEOUT:
                r, _, _ = select.select([self.__sock], [], [], koemyd.const.SOCKET_TIMEOUT)
                if self.__sock in r:
                    _last_access = time.time()

                    c = self.rx(koemyd.const.SOCKET_BUFSIZE)
                    if c: d += c
                    else:
                        raise ConnectionSocketError("p#%s:%d:disconnected" % self.__peer_address)
            else:
                raise ConnectionTimeoutError("p#%s:%d:connection timeout!" % self.__peer_address)
        self.__sock.setblocking(1)

        if not '\n' in d:
            raise ConnectionSocketError("p#%s:%d:maximum length exceeded!" % self.__peer_address)

        if '\r' in d:
            i = d.find('\r')
            l = d[:i]
            i += 2 # i + 2: do not cache next CRLF
        else:
            i = d.find('\n')
            l = d[:i]
            i += 1 # i + 1: do not cache next LF

        self.cache += d[i:]
        if self.cache:
            koemyd.logger.data("c#%s:s#%s" % (self.__link.uuid, self.uuid),
                                   "cw:%s" % koemyd.util.dump(self.cache))

        return str(l)

    def close(self):
        if not type(self.__peer_address) == tuple: return

        try:
            self.__sock.shutdown(socket.SHUT_RDWR)
            self.__sock.close()
        except socket.error as e:
            if e.errno in [errno.ENOTCONN, errno.EBADF]: return
            else:
                raise e

        koemyd.logger.info("c#%s:s#%s" % (self.__link.uuid, self.uuid),
                           "p#%s:%d:connection closed"
                           % self.__peer_address)

    def reset(self):
        self.close()
        self.setup()

class ConnectionSocketError(ConnectionError): pass
class ConnectionTimeoutError(ConnectionSocketError): pass

