#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# lsusb to check device name
# dmesg | grep "tty" to find port name

# Commands:

# lp: Check lens presence
# in: Open aperture
# st: Stop driving focus and aperture
# is1: IS unlock
# ix: IS shift in x-direction (ex: ix100)
# iy: IS shift in y-direction (ex: iy100)
# is0: IS lock
# pi: Print IS position
# mf: Move focus incremental (ex: mf100)
# fa: Move focus to absolute setpoint (ex: fa100)
# mi: Move focus to infinity
# mz: Move focus to near
# la: Update fmax (infinity) and fmin (near)
# pf: Print focus position information
# sf0: Focus position information is reset to 0

import serial,time,sys

if __name__ == '__main__':

    if (sys.version_info[0] != 3):
        raise Exception("Sorry - I only work under python3")
    
    print('Running. Press CTRL-C to exit.')
    with serial.Serial("/dev/ttyACM0",
                        baudrate=9600,
                        parity=serial.PARITY_NONE,
                        bytesize=serial.EIGHTBITS,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1) as arduino:
        time.sleep(0.1) #wait for serial to open
        if arduino.isOpen():
            print("{} connected!".format(arduino.port))
            try:
                while(True):
                    cmd = input('Enter command: ')
                    cmd = cmd + '\n'
                    arduino.flush()
                    arduino.write(cmd.encode())
                    line = ""
                    while(True):
                        if arduino.inWaiting()>0:
                            time.sleep(0.01)
                            c = arduino.read().decode()
                            if c == '\n':
                                break
                            line = line + c
                    print("Received: {}\n".format(line))
                    arduino.flush()
                
            except KeyboardInterrupt:
                arduino.close()
                print("KeyboardInterrupt has been caught.")
