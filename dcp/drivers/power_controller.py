#!/usr/bin/python3
# -*- coding: utf-8 -*-

import serial
import time
import sys
import os
import argparse
import socket

command_list = [
    '',
    'HIGH-LEVEL COMMANDS:',
    '',
    'QUIT          Exit this program',
    'HELP          Display this list',
    'VERBOSE       Toggle current verbose state',
    '',
    'POWER CONTROLLER COMMANDS:',
    '',
    'P#            Print status.',
    'PE:bbbb       Set power status on boot. Every number represents 1-4 power outputs (0=Off, 1=On)',
    'P1:b          On/Off power 4x12V outputs (0=Off, 1=On)',
    'P2:n          On/Off power DSLR output (0=Off, 1=On).',
    '              n can also accept values of: 3, 5, 8, 9, 12 which represent volts, and which',
    '              set the coresponding DSLR output. However, the default behaviour is to limit the',
    '              values of n to only 0, 1, 3 and 5 to avoid risking the Canon lenses. This can be',
    '              overridden with the --dangerous switch.'
    'P3:nnn        PWM duty cycle on DewA output. X=0-255 (0-100%)',
    'P4:nnn        PWM duty cycle on DewB output. X=0-255 (0-100%)',      
    'PA            Print power and sensor readings. Returns a long string in the following format:',
    ''
    '                       PPBA:voltage:current_of_12V_outputs_:temp:humidity:dewpoint:...',
    '                       quadport_status:adj_output_status:dew1_power:dew2_power:autodew_bool:...',
    '                       pwr_warn:pwradj',
    ''
    '              where the fields have the following meanings:',
    ''
    '                       voltage = input voltage in volts decimal (e.g. 12.2)',
    '                       current = quad 12V output current 0-1024 (need to ',
    '                                 convert to Amps by dividing by 65 (better to',
    '                                 use output from the PS command.',
    '                       temp = temperate in Celsius degrees (decimal, e.g. 20.2)',
    '                       humidity = relative humidity in percent (integer, e.g. 59)',
    '                       quadport status = Boolean 0 or 1 (1 means port is ON,0 means port is OFF)',
    '                       adj_output_status = Boolean 0 or 1 (1 means port is ON,0 means port is OFF)',
    '                       dew1_power = Power of DewA channel -duty cycle 0-255',
    '                       dew2_power = Power of DewB channel -duty cycle 0-255',
    '                       autodew_bool = Boolean for autodew function (controls power of both Dew',
    '                                      channels): 0is OFF, 1 is ON',
    '                       pwr_warn = Boolean. 1 means power alert (short wire detection / output overload).',
    '                                  This is a generic flag for any 12V and DewA, DewB power outputs.',
    '                       pwradj   = Adjustable Output: Selected voltage in EEPROM (3,5,8,9,12)',
    'PS            Print power consumption statistics. Returns a long string in the following format:',
    '',
    '                       PS:averageAmps:ampHours:wattHours:uptime_in_millisec',
    '',
    'PC            Print power metrics. Returns a long string in the following format (with currents in amps and',
    '              no conversion is required):'
    '',
    '                       PC:total_current:current_12V_outputs:current_dewA:current_dewB:uptime_in_millisec',
    '',
    'PR            Prints discovered I2C devices plugged into EXT port',
    'DA            (Auto) dew aggresiveness (0-255; default 210)',
    'PD:b          Enable/disable auto dew feature (b=0,1; PD:99 reports',
    '              auto dew aggressiveness value',
    'PV            Firmware version',
    'PI            Reset I2C channel',
    'PL:b          On/off LED indicator (0=Off,1=On)',
    '',
    'COMMANDS YOU SHOULD PROBABLY NOT USE:',
    '',
    'XS            External motor comands. See manual.',
    'PF            Reboot device/reload firmware.',
    '',
    'NOTES:',
    '',
    'All commands are case insensitive. Abbreviations used above have the',
    'following meaning:',
    '',
    'nnn = one or more digits',
    'b = Boolean (0 or 1)',
    ''
]


def main():

    if (sys.version_info[0] != 3):
        raise Exception("Sorry - I only work under python3")

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", default=False, action="store_true", 
                        help="increase output verbosity (default = False)")
    parser.add_argument("-d", "--dangerous", default=False, action="store_true", 
                        help="allow dangerous commands (default = False)")
    parser.add_argument("-w", "--wait_time", default=2.0, type=float, 
                        help="wait time in seconds before power controller communication begins (default = 2)")
    parser.add_argument("-p", "--port", default="/dev/ttyUSB0", type=str, 
                        help="port that the power controller is on (default = /dev/ttyUSB0)")
    parser.add_argument("-c", "--command", 
                        help="single command to execute")

    args = parser.parse_args()

    verbose = args.verbose
    dangerous = args.dangerous
    wait_time = args.wait_time
    cmd = args.command
    port = args.port


    if cmd != None: 
        interactive = False
    else:
        interactive = True
        cmd = None
    
    if verbose:
        print('Running. Press CTRL-C to exit.')

    with serial.Serial(port,
                        baudrate=9600,
                        parity=serial.PARITY_NONE,
                        bytesize=serial.EIGHTBITS,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1) as pegasus:
        time.sleep(0.1) #wait for serial port to open
        if pegasus.isOpen():
            if verbose:
                print("Serial port is open.")
            try:
                while True:
                    # This is the main REPL loop.

                    if interactive:
                        cmd = input('Enter command: ')

                    else:
                        # Command supplied as a one-shot.
                        if verbose:
                            print("Getting command from the command-line with the -c switch.")
                            print("Waiting {:.1f} seconds before sending command".format(wait_time))
                        time.sleep(wait_time)

                    cmd = cmd + '\n'
                    cmd = cmd.upper()
                    if "QUIT" in cmd:
                        pegasus.close()
                        sys.exit()
                    if "HELP" in cmd:
                        [print(line) for line in command_list]
                        if interactive:
                            continue
                        else:
                            pegasus.close()
                            sys.exit()
                    if "VERB" in cmd:
                        verbose = not verbose
                        print("Verbosity toggled. Now set to {}".format(verbose))
                        if interactive:
                            continue
                        else:
                            pegasus.close()
                            sys.exit()

                    if not dangerous and (("P2:8" in cmd) or ("P2:9" in cmd) or ("P2:12" in cmd)):
                        print("Risky commands are not allowed without the --dangerous switch.")
                        if interactive:
                            continue
                        else:
                            pegasus.close()
                            sys.exit()

                    pegasus.flush()
                    pegasus.write(cmd.encode())
                    line = ""
                    lines = []
                    while(True):
                        if pegasus.inWaiting()>0:
                            time.sleep(0.01)
                            c = pegasus.read().decode()
                            if c == '\n':
                                lines.append(line)
                                if verbose:
                                    print("  Received: {}".format(line.lstrip().rstrip()))
                                break
                            line = line + c
                    print("Result: {}\n".format(line))
                    if "PA" in cmd:
                        (dummy,v,c,t,h,dp,qp,ao,d1p,d2p,ad,pwn,padj) = line.rstrip().split(":")
                        print(f"Input voltage: {v} [V]")
                        print("Current being drawn: {:.2f} [A]".format(float(c)/65))
                        print(f"Temperature: {t} [C]")
                        print(f"Humidity: {h} [%]")
                        print(f"Dewpoint: {dp} [C]")
                        print(f"Quadport power status: {qp} [0=Off, 1=On]")
                        print(f"Adjustable port power status: {ao} [0=Off, 1=On]")
                        print(f"Duty cycle of DewA port: {d1p} [0-255]")
                        print(f"Duty cycle of DewB port: {d2p} [0-255]")
                        print(f"Autodew status: {ad} [0=Off, 1=On]")
                        print(f"Power warning status: {pwn} [0=None, 1=Alert]")
                        print(f"Adjustable port voltage: {padj} [V]")
                        print("")
                    pegasus.flush()

                    if not interactive:
                        # one-shot!
                        pegasus.close()
                        sys.exit()
            
            except KeyboardInterrupt:
                pegasus.close()
                print("KeyboardInterrupt has been caught.")
                sys.exit()

if __name__ == '__main__':
    main()

