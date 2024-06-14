#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import serial
import time
import sys
import os
import argparse
import socket

command_list = [
    '',
    'High Level Commands:',
    '',
    'quit          Exit this program',
    'help          Display this list',
    'verbose       Toggle current verbose state',
    '',
    'Camera Commands:',
    '',
    'fa<number>    Move focus to absolute setpoint (e.g.: fa11000)',
    'in            Open aperture',
    'is1           IS unlock',
    'is0           IS lock',
    'ix<number>    IS shift in x-direction (e.g.: ix100)',
    'iy<number>    IS shift in y-direction (e.g.: iy100)',
    'la            Update fmax (infinity) and fmin (near)',
    'lp            Check lens presence',
    'mf<number>    Move focus incremental (e.g.: mf100)',
    'mi            Move focus to infinity',
    'mz            Move focus to near',
    'pf            Print focus position information',
    'pi            Print IS position',
    'sf0           Focus position information is reset to 0', 
    'st            Stop driving focus and aperture',
    'dc            Disable circuit',
    'ec            Enable circuit',
    ''
]


def main():

    if (sys.version_info[0] != 3):
        raise Exception("Sorry - I only work under python3")

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", default=False, action="store_true", 
                        help="increase output verbosity (default = False)")
    parser.add_argument("-w", "--wait_time", default=2.0, type=float, 
                        help="wait time in seconds before camera communication begins (default = 2)")
    parser.add_argument("-p", "--port", default="/dev/ttyACM0", 
                        help="port name (default = /dev/ttyACM0)")
    parser.add_argument("-c", "--command", 
                        help="single command to execute")
    parser.add_argument("-s", "--server", default=False, action="store_true", 
                        help="run in server mode (default = False)")

    args = parser.parse_args()

    verbose = args.verbose
    wait_time = args.wait_time
    serial_port = args.port
    server = args.server
    cmd = args.command

    HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    PORT = 65432        # Port to listen on (non-privileged ports are > 1023)
    listening = False

    # If the server is selected that overrides everything. If the server is
    # not selected but a command is given with the -c switch, the command
    # is executed.
    if server == True:
        interactive = False
        cmd = None
    elif cmd != None: 
        interactive = False
        server = False
    else:
        interactive = True
        server = False
        cmd = None
    
    if verbose:
        print('Running. Press CTRL-C to exit.')

    with serial.Serial(serial_port,
                       baudrate=9600,
                       parity=serial.PARITY_NONE,
                       bytesize=serial.EIGHTBITS,
                       stopbits=serial.STOPBITS_ONE,
                       timeout=1) as arduino:
        time.sleep(0.1) #wait for serial port to open
        if arduino.isOpen():
            if verbose:
                print("Serial port is open.")
            try:
                while True:
                    # This is the main REPL loop.

                    if server:
                        if not listening:
                            # Set up the socket.
                            try:
                                if verbose:
                                    print("Activating server.")
                                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                s.bind((HOST, PORT))
                                s.listen()
                                listening = True
                            except OSError:
                                print("Error setting up socket.")
                                arduino.close()
                                s.close()
                                sys.exit()
                        try:
                            conn, addr = s.accept()  
                            if verbose:
                                print(f"Connection opened by: {addr}")
                            cmd = conn.recv(1024)
                            if not cmd:
                                break
                            conn.sendall(cmd)
                            cmd = cmd.decode()   
                        except OSError:
                                print("Error listening on socket.")
                                arduino.close()
                                s.close()
                                sys.exit()

                    elif interactive:
                        cmd = input('Enter command: ')

                    else:
                        # Command supplied as a one-shot.
                        if verbose:
                            print("Getting command from the command-line with the -c switch.")
                            print("Waiting {:.1f} seconds before sending command".format(wait_time))
                        time.sleep(wait_time)

                    cmd = cmd + '\n'
                    if "quit" in cmd.lower():
                        if server:
                            conn.sendall(b"Shutting down server.")
                            s.close()
                        arduino.close()
                        sys.exit()
                    if "help" in cmd.lower():
                        [print(line) for line in command_list]
                        if interactive:
                            continue
                        else:
                            if server:
                                conn.sendall(b"Help printed to console.")
                                continue
                            else:
                                arduino.close()
                                sys.exit()
                    if "verbose" in cmd.lower():
                        verbose = not verbose
                        print("Verbosity toggled. Now set to {}.".format(verbose))
                        if interactive:
                            continue
                        else:
                            if server:
                                conn.sendall(b"Verbosity state toggled.")
                                continue
                            else:
                                arduino.close()
                                sys.exit()

                    arduino.flush()
                    arduino.write(cmd.encode())
                    line = ""
                    lines = []
                    while(True):
                        if arduino.inWaiting()>0:
                            time.sleep(0.01)
                            c = arduino.read().decode()
                            if c == '\n':
                                lines.append(line)
                                if verbose:
                                    print("  Received: {}".format(line.lstrip().rstrip()))
                                if "Done" in line:
                                    break
                                line = ""
                            line = line + c
                    result = lines[-2].lstrip().rstrip()
                    print("Result: {}\n".format(result))
                    if server:
                        conn.sendall(result.encode())
                    arduino.flush()

                    if not interactive and not server:
                        # one-shot!
                        arduino.close()
                        sys.exit()
            
            except KeyboardInterrupt:
                arduino.close()
                print("KeyboardInterrupt has been caught.")
                if server:
                    s.close()
                sys.exit()

if __name__ == '__main__':
    main()

