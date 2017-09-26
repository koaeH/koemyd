# vi:ts=4:sw=4:syn=python

import urlparse

import koemyd.base
import koemyd.const

class HTTPMessage(koemyd.base.UUIDObject):
    def __init__(self, line):
        super(HTTPMessage, self).__init__()

        self.line, self.headers = line, HTTPHeaders()

    @property
    def head(self):
        m = bytearray()
        for header in self.headers.iteritems():
            m += "%s: %s" % header
            m += koemyd.const.CRLF

        return str(m)

class HTTPRequest(HTTPMessage):
    def __init__(self, line=str()):
        super(HTTPRequest, self).__init__(line)

        try:
            self.method, self.uri, self.http_version = line.split()
        except ValueError:
            raise HTTPRequestError(400, "request:line:could not parse")

        if self.method not in map(str.upper, koemyd.const.HTTP_METHODS_ALLOWED):
            raise HTTPRequestError(405, "request:%s:not allowed" % self.method)

class HTTPResponse(HTTPMessage):
    def __init__(self, line=str()):
        super(HTTPResponse, self).__init__(line)

        try:
            self.http_version, _s_code, self.reason = line.split(None, 2)
            self.code    = int(_s_code)
        except ValueError as e:
            raise HTTPResponseError(502, "response:line:could not parse")

    @property
    def expect_body(self): # cf. Section 3.3 of [RFC7230]
        return True if self.code not in [100, 101, 204, 304] else False

class HTTPHeaders(dict):
    def __init__(self, *args, **kwargs):
        super(HTTPHeaders, self).__init__(*args, **kwargs)

    def __contains__(self, k): return k.title() in map(str.title, self.keys())

    def __getitem__(self, k):
        for cs_k in self.keys():
            if k.title() == cs_k.title(): k = cs_k
        return super(HTTPHeaders, self).__getitem__(k)

    def __setitem__(self, k, v):
        for cs_k in self.keys():
            if k.title() == cs_k.title(): k = cs_k
        super(HTTPHeaders, self).__setitem__(k, v.strip())

    def __delitem__(self, k):
        for cs_k in self.keys():
            if k.title() == cs_k.title():
                super(HTTPHeaders, self).__delitem__(cs_k)

    def __fn_order(self, i, p=koemyd.const.HTTP_HEADERS_SORT_PRIO_KEYS):
        k, v = map(str.title, i)
        p = tuple(map(str.title, p))
        return (p.index(k) if k in p else len(p), i)

    def iteritems(self):
        i = super(HTTPHeaders, self).iteritems()
        headers = sorted(i, key=self.__fn_order)
        for k, v in headers: yield (k, v)

    @staticmethod
    def parse(line):
        if ':' not in line:
            raise HTTPHeaderError(400, "header:missing colon")
        else:
            try:
                return tuple(line.split(':', 1))
            except ValueError:
                return tuple(line, str())

class HTTPChunk(object):
    def __init__(self): self.size, self.data = int(), str()

class HTTPError(Exception):
    def __init__(self, c, l): self.code, self.line = c, l

    def __str__(self):
        return "e#%04d:%s" % (self.code, self.line)

class HTTPResponseError(HTTPError): pass
class HTTPRequestError(HTTPError): pass
class HTTPHeaderError(HTTPError): pass
