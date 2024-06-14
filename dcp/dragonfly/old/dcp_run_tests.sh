#!/usr/bin/env bash

# Make sure this being run with root permission.
if [ "$(id -u)" -ne 0 ]; then echo "Please run as root using 'sudo'." >&2; exit 1; fi

# Determine name of the directory holding the script.
dirname=$(dirname "$0")

# Use BATS to run the test suite.
sudo $dirname/../test/bats/bin/bats $dirname/../test/test.bats