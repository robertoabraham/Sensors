#!/usr/bin/env bash

# Make sure this being run with root permission.
if [ "$(id -u)" -ne 0 ]; then echo "Please run as root using 'sudo'." >&2; exit 1; fi

# Determine name of the directory holding the script.
dirname=$(dirname "$0")

# Send commands to close the servers, ignoring errors if they exist.
$dirname/dcp_client.py -s powerbox quit 2> /dev/null
$dirname/dcp_client.py -s aluma quit 2> /dev/null 
$dirname/dcp_client.py -s starchaser quit 2> /dev/null
$dirname/dcp_client.py -s fastlens quit 2> /dev/null
$dirname/dcp_client.py -s apmount quit 2> /dev/null

# In case that didn't work, use a hammer to kill all DCP servers running on the machine.
pkill dcp_powerbox_server 
pkill dcp_sbig_server 
pkill dcp_fastlens_server
pkill dcp_apmount_server
