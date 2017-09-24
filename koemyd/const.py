# vi:ts=4:sw=4:syn=python

PROGRAM_NAME  = "koemyd"
PROGRAM_DESC  = "a Minimalistic HTTP/1.1 Link Procurator"

VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION = "%d.%d" % (VERSION_MAJOR, VERSION_MINOR)

SETTINGS_PROGRAM_CONFIG_FILE = "koemyd.conf"

SETTINGS_DEFAULT_LISTEN_ADDR = "0.0.0.0"
SETTINGS_DEFAULT_LISTEN_PORT = "11811"

DAEMON_MAX_CONCURRENCY = 128

DATA_DEBUGGING = 0 # >.<

SOCKET_BUFSIZE = 4096 if not DATA_DEBUGGING else 16
SOCKET_TIMEOUT = 30.0 if not DATA_DEBUGGING else 60

HTTP_CRLF = CRLF = "\r\n"

HTTP_METHODS_ALLOWED = [        # cf. [RFC2616] & [RFC7230]
    "CONNECT",
    "OPTIONS", "GET", "POST",
    "PUT", "DELETE", "TRACE", "HEAD",
]
HTTP_HEADERS_SKIP_TO_SERVER = [ # cf. [RFC2616] & [RFC7230]
    "Proxy-Connection", "Proxy-Authorization",
    "Transfer-Encoding", "TE", "Trailers",
    "Upgrade",
]
HTTP_HEADERS_SKIP_TO_CLIENT = [ # cf. [RFC2616] & [RFC7230]
    "Proxy-Authenticate", "Keep-Alive",
]
HTTP_HEADERS_SORT_PRIO_KEYS = [ # koemyd.struct.HTTPHeaders
    "Host", "Connection",
    "Proxy-Connection",
    "Authorization",
    "User-Agent",
]
