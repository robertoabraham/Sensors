#!/usr/bin/env bash

# Make sure this being run with root permission.
if [ "$(id -u)" -ne 0 ]; then echo "Please run as root using 'sudo'." >&2; exit 1; fi

# Make sure the dragonfly User can display X11 applications being run from the root account.
FILE=/home/dragonfly/.Xauthority
if test -f "$FILE"; then
    cp /home/dragonfly/.Xauthority /root
fi

# Determine name of the directory holding the script.
dirname=$(dirname "$0")

# Kill existing servers
$dirname/dcp_kill_servers.sh

# Start up each server in turn.
$dirname/dcp_powerbox_server.py &
sleep 1
$dirname/dcp_apmount_server.py -p /dev/ttyUSB1 &
sleep 1
$dirname/dcp_sbig_server.py -c aluma &
sleep 3
$dirname/dcp_sbig_server.py -c starchaser &
sleep 1
$dirname/dcp_fastlens_server.py &

echo "All DCP servers started (running in the background)."
