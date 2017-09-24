# vi:ts=4:sw=4:syn=python

import sys

import koemyd.const

__version__ = koemyd.const.VERSION

if sys.version_info < (2, 6):
    raise RuntimeError, "oops: python 2.6 or higher is required"
