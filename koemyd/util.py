# vi:ts=4:sw=4:syn=python

import os
import sys

import traceback

def dump(d): return ':'.join("%02x" % ord(d_b) for d_b in str(d))

def hook(exc_type, value, tb):
    exc = traceback.format_exception(exc_type, value, tb)
    sys.stderr.write(os.linesep.join(exc))
    sys.stderr.write(os.linesep)
