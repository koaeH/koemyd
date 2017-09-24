#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:sw=4:syn=python

import os
import sys

import koemyd.util

if __name__ != "__main__":
    sys.stderr.write("oops: this is the entry point, it cannot be imported.")
    sys.stderr.write(os.linesep)
    sys.exit(1)

sys.excepthook = koemyd.util.hook
from koemyd.main import main
main(sys.argv[1:])
