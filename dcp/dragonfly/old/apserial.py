# This was an experiment in controlling AP mount serial port without using
# PySerial. It is taken from some code on the internet for controlling
# an Arduino (arduinoserial.py).
#
# I did this because for the longest time I was trying to use a
# Keyspan (Tripp-Lite) USB-Serial Adapter with an ARM64 Linux Raspberry Pi,
# not realizing that the driver for this serial adapter is buggy. 
# 
# I'll keep this code around because it's interesting and it probably works, 
# though I went back to PySerial once I figured out that the issue I was
# having was due to the USB-Serial adapter and not PySerial.

import termios
import os
import sys
import time

# Map from the numbers to the termios constants (which are pretty much
# the same numbers).

BPS_SYMS = {
    4800: termios.B4800,
    9600: termios.B9600,
    19200: termios.B19200,
    38400: termios.B38400,
    57600: termios.B57600,
    115200: termios.B115200
}

# Indices into the termios tuple.
IFLAG = 0
OFLAG = 1
CFLAG = 2
LFLAG = 3
ISPEED = 4
OSPEED = 5
CC = 6


def bps_to_termios_sym(bps):
    return BPS_SYMS[bps]


class SerialPort(object):
    """Represents a serial port connected to an Astro-Physics mount."""
    def __init__(self, port, bps=9600):
        self.port = port
        self.baud = bps
        self.fd = None
        
    def __del__(self):
        if self.fd is not None:
            os.close(self.fd)
        
    def connect(self):
        """Takes the string name of the serial port (e.g.
        "/dev/tty.usbserial","COM1") and a baud rate (bps) and connects to
        that port at that speed and 8N1. Opens the port in fully raw mode
        so you can send binary data.
        """
        self.fd = os.open(self.port, os.O_RDWR | os.O_NOCTTY | os.O_NDELAY)
        attrs = termios.tcgetattr(self.fd)
        bps_sym = bps_to_termios_sym(self.baud)
        # Set I/O speed.
        attrs[ISPEED] = bps_sym
        attrs[OSPEED] = bps_sym

        # 8N1
        attrs[CFLAG] &= ~termios.PARENB
        attrs[CFLAG] &= ~termios.CSTOPB
        attrs[CFLAG] &= ~termios.CSIZE
        attrs[CFLAG] |= termios.CS8
        # No flow control
        attrs[CFLAG] &= ~termios.CRTSCTS

        # Turn on READ & ignore contrll lines.
        attrs[CFLAG] |= termios.CREAD | termios.CLOCAL
        # Turn off software flow control.
        attrs[IFLAG] &= ~(termios.IXON | termios.IXOFF | termios.IXANY)

        # Make raw.
        attrs[LFLAG] &= ~(termios.ICANON |
                          termios.ECHO |
                          termios.ECHOE |
                          termios.ISIG)
        attrs[OFLAG] &= ~termios.OPOST

        # It's complicated--See
        # http://unixwiz.net/techtips/termios-vmin-vtime.html
        attrs[CC][termios.VMIN] = 0
        attrs[CC][termios.VTIME] = 20
        termios.tcsetattr(self.fd, termios.TCSANOW, attrs)

    def disconnect(self):
        os.close(self.fd)

    def read_until(self, until):
        buf = ""
        done = False
        while not done:
            n = os.read(self.fd, 1)
            if n == b'':
                time.sleep(0.01)
                continue
            buf = buf + n.decode()
            if n == until:
                done = True
        return buf
    
    def read_one_char(self):
        n = os.read(self.fd, 1)
        return n.decode()

    def write(self, str):
        os.write(self.fd, str.encode())

    def write_byte(self, byte):
        os.write(self.fd, chr(byte))