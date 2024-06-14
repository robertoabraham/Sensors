#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# lsusb to check device name
# dmesg | grep "tty" to find port name

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
        command = sys.argv[1]
        if arduino.isOpen():
            print("{} connected!".format(arduino.port))
            try:
                n = True
                while(n):
                    cmd = command
                    a = input("this makes it work")

                    cmd = cmd + '\n'
                    arduino.flush()
                    arduino.write(cmd.encode())
                    line = ""
                    while(True):
                        #time.sleep(0.1)
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
