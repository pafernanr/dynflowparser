#!/usr/bin/python3
import os
import sys

try:
    sys.path.insert(0, os.getcwd())
    from dynflowparser import DynflowParser
except KeyboardInterrupt:
    raise SystemExit()


def main():
    DynflowParser().main()
