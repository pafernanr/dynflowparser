#!/usr/bin/python3
import os
import sys

try:
    sys.path.insert(0, os.getcwd())
    from dynflowparserexport import DynflowParserExport
except KeyboardInterrupt:
    raise SystemExit()


def main():
    DynflowParserExport().main()
