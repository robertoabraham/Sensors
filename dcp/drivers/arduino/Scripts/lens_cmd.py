#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# lsusb to check device name
# dmesg | grep "tty" to find port name

# Commands:

# lp:  Check lens presence
# in:  Open aperture
# st:  Stop driving focus and aperture
# is1: IS unlock
# ix:  IS shift in x-direction (ex: ix 100)
# iy:  IS shift in y-direction (ex: iy 100)
# is0: IS lock
# pi:  Print IS position
# mf:  Move focus incremental (ex: mf 100)
# fa:  Move focus to absolute setpoint (ex: fa 100)
# mi:  Move focus to infinity
# mz:  Move focus to near
# la:  Update fmax (infinity) and fmin (near)
# pf:  Print focus position information
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
        msg = ""
        if arduino.isOpen():
            print("{} connected!".format(arduino.port))
            try:
                n = True
                while(n):
                    cmd = ""
                    for i in range(len(sys.argv) - 1):
                        cmd = cmd + sys.argv[i+1]
                    cmd = cmd + '\n'
                    arduino.flush()
                    arduino.write(cmd.encode())
                    line = ""
                    while(True):
                        # print(arduino.inWaiting())
                        if arduino.inWaiting()>0:
                            time.sleep(0.01)
                            c = arduino.read().decode()
                            if c == '\n':
                                print("  Received: {}".format(line.lstrip().rstrip()))
                                if "Done" in line:
                                    break
                                line = ""
                            line = line + c
                    arduino.flush()
                    n = False
                
            except KeyboardInterrupt:
                arduino.close()
                print("KeyboardInterrupt has been caught.")
