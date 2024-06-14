#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# lsusb to check device name
#dmesg | grep "tty" to find port name

import serial,time,sys

if __name__ == '__main__':

    if (sys.version_info[0] != 3):
        raise Exception("Sorry - I only work under python3")
  
    # Get the command to send to the lens.
    cmd = sys.argv[1]
    cmd = cmd + '\n'

    with serial.Serial("/dev/ttyACM0", 9600, timeout=1) as arduino:
        time.sleep(0.1) #wait for serial port to open
        if arduino.isOpen():
            print("{} connected!".format(arduino.port))
            try:
                print("Sending command: {}".format(cmd))
                arduino.write(cmd.encode())
                while True:
                    time.sleep(0.1) #wait for arduino to answer
                    while arduino.inWaiting()==0: pass
                    if  arduino.inWaiting()>0: 
                        answer=arduino.readline().decode()
                        print(answer.rstrip())
                        if ("Done." in answer):
                            break
            except KeyboardInterrupt:
                print("KeyboardInterrupt has been caught.")
