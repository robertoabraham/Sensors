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
                        stopbits=serial.STOPBITS_ONE,
                        parity=serial.PARITY_NONE,
                        bytesize=serial.EIGHTBITS,
                         timeout=1) as arduino:
        time.sleep(0.1) #wait for serial to open
        if arduino.isOpen():
            print("{} connected!".format(arduino.port))
            try:
                cmd = input('Enter command: ')
                cmd = cmd + '\n'
                arduino.flush()
                arduino.write(cmd.encode())
                while True:
                    time.sleep(0.1) #wait for arduino to answer
                    while arduino.inWaiting()==0: 
                        time.sleep(0.1)
                        pass
                    if arduino.inWaiting()>0: 
                        answer=arduino.readline().decode()
                        print(answer.rstrip())
                        if ("Done." in answer):
                            arduino.close()
                            break
            except KeyboardInterrupt:
                print("KeyboardInterrupt has been caught.")
