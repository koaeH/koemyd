# vi:ts=4:sw=4:syn=python

import urlparse

import koemyd.trans
import koemyd.struct

class ClientRequest(koemyd.struct.HTTPRequest):
    def __init__(self, line=str()):
        super(ClientRequest, self).__init__(line)

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

class ServerRequestError(koemyd.struct.HTTPError): pass

class ServerResponse(koemyd.struct.HTTPResponse):
    def __init__(self, line):
        super(ServerResponse, self).__init__(line)

        self.__coder = None

    def __set_coder(self):
        if "Transfer-Encoding" in self.headers:
            if "chunked" == self.headers["Transfer-Encoding"].lower():
                self.__coder = koemyd.trans.ChunkDecoder()
            else:
                raise ServerResponseError(502, "%s:unsupported transfer-encoding")
        elif not "Content-Length" in self.headers:
            self.headers["Transfer-Encoding"] = "chunked"
            self.__coder = koemyd.trans.ChunkEncoder()

        return self.__coder

    @property
    def coder(self): return self.__coder if self.__coder else self.__set_coder()

    @property
    def is_persistent(self):
        if "Connection" in self.headers:
            if self.headers["Connection"].lower() == "keep-alive":
                return True

        return False

class ServerResponseError(koemyd.struct.HTTPError): pass
