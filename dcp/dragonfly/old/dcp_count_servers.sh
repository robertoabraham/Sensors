#!/usr/bin/env bash

# Note the space at the end of the regular expression below. That's important
# as otherwise we match this script in the process table.
ps -ef | grep -E 'dcp_.*_server' | grep -v grep | grep -v dcp_count_server | wc | awk '{print $1}'
