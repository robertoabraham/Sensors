#!/home/dragonfly/miniforge3/envs/active_optics/bin/python
# -*- coding: utf-8 -*- 

# Echo client program
import socket
import argparse
import json
import sys
import logging

from dragonfly import state as state
from dragonfly import dcp as dcp

# Setup logging to write to both the screen and a log file.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(
        "/home/dragonfly/dragonfly-arm/active_optics/dashboard/log.txt"),
        logging.StreamHandler()
    ]
)

parser = argparse.ArgumentParser(
                  prog='dcp_client',
                  description='Sends general DCP command to Dragonfly servers.',
                  epilog='Copyright 2023 - Team Dragonfly')

parser.add_argument("-s", "--server", default="aluma", 
                    help="Name of DCP server. (default=aluma)")
parser.add_argument("-c", "--compact", default=False, action='store_true', 
                    help="Do not pretty-print the output.")
parser.add_argument("-a", "--asynchronous", default=False, action='store_true', 
                    help="Operate asynchronously.")
parser.add_argument("verb", type=str, 
                    help="Verb.")
parser.add_argument("noun", type=str, nargs='?', 
                    help="Noun.", default=None)
parser.add_argument("arg1", type=str, nargs='?', 
                    help="First argument.", default=None)
parser.add_argument("arg2", type=str, nargs='?', 
                    help="Second argument.", default=None)
args = parser.parse_args()

try:
    output = dcp.send(args.server, args.verb, args.noun, args.arg1, args.arg2, 
                      asynchronous=args.asynchronous)
    if (args.compact):
        print(output)
    else:
        # Format the output as an indented (if needeed) JSON object. Note that
        # this means that strings will have double quotes around them.
        print(json.dumps(output,indent=2))
except dcp.DCPServerError as e:
    print(e)
    sys.exit(1)


