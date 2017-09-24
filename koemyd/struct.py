# vi:ts=4:sw=4:syn=python

import urlparse

import koemyd.base
import koemyd.const

class HTTPMessage(koemyd.base.UUIDObject):
    def __init__(self, line=str()):
        # e.g., GET /c.php HTTP/1.1
        self.message_line = self.line = line
        
        # e.g., {"Host":"remote.test","TE":"",...}
        self.headers = koemyd.struct.HTTPHeaders()

    @property
    def message_head(self):
        m = str()
        for header in self.headers.iteritems():
            m += "%s: %s" % header
            m += koemyd.const.CRLF

        return m

class HTTPRequest(HTTPMessage):
    def __init__(self, line=str()):
        super(HTTPRequest, self).__init__(line)

        self.method       = str() # e.g., POST
        self.uri          = str() # e.g., /f.php
        self.http_version = str() # e.g., HTTP/1.1

        # e.g., GET /~koaeH/ HTTP/1.1
        self.request_line = self.line

        self.__parse()

    def __parse(self):
        try:
            self.method, self.uri, self.http_version = self.line.split()
        except ValueError:
            raise HTTPRequestError(400, "request:could not parse line!")

        if self.method not in map(str.upper, koemyd.const.HTTP_METHODS_ALLOWED):
            raise HTTPRequestError(405, "request:%s:method not allowed!" % self.method)

        if self.http_version not in ["HTTP/0.9", "HTTP/1.0", "HTTP/1.1"]:
            raise HTTPRequestError(505, "request:%s:not supported" % self.http_version)

class HTTPResponse(HTTPMessage):
    def __init__(self, line=str()):
        super(HTTPResponse, self).__init__(line)

        self.http_version = str() # e.g., HTTP/1.1
        self.code         = int() # e.g., 200
        self.reason       = str() # e.g., OK

        # e.g., HTTP/1.1 204 No Content
        self.status_line = self.line

        self.__parse()

    def __parse(self):
        try:
            self.http_version, _c, _r = self.line.split(None, 2)
            self.reason = _r.strip()
            self.code = int(_c)
        except ValueError as e:
            raise HTTPResponseError(502, "response:could not parse line")

    @property
    def expect_body(self): # cf. Section 4.3 of [RFC2616]
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
        if ':' in line:
            try:
                return line.split(':', 1)
            except ValueError:
                return line, str()
        else:
            raise HTTPHeaderError(400, "header:missing colon")

class HTTPChunk(object):
    def __init__(self): self.size, self.data = int(), str()

class HTTPError(Exception):
    def __init__(self, c, l): self.code, self.line = c, l

    def __str__(self):
        return "e#%04d:%s" % (self.code, self.line)

class HTTPResponseError(HTTPError): pass
class HTTPRequestError(HTTPError): pass
class HTTPHeaderError(HTTPError): pass
