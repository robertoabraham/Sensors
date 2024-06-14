#!/home/dragonfly/miniforge3/envs/active_optics/bin/python
# -*- coding: utf-8 -*- 

import os
import threading as th
import logging
import json
import socket
import argparse
import serial
import time

from dragonfly import dcp as dcp
from dragonfly import powerbox as powerbox
from dragonfly import state as state
from dragonfly import utility as utility

# Setup logging to write to both the screen and a log file.
logging.basicConfig(
   level=logging.INFO,
   format="%(asctime)s [%(levelname)s] %(message)s",
   handlers=[
       logging.FileHandler("/home/dragonfly/dragonfly-arm/active_optics/dashboard/log.txt"),
       logging.StreamHandler()
   ])

recognized_verbs = []
powerbox_busy = False
subsystem_name = "powerbox"


# Powerbox operations are handled in a separate thread from the main I/O loop. The 
# operations thread is defined here.

def powerbox_command_thread(pegasus, verb, noun, arg1, arg2):
    global powerbox_busy
    global recognized_verbs
    powerbox_busy = True
    state.set_state_variable(subsystem_name,"busy", True)    
        
    try:
   
        if verb.lower()=="activate":
            
            if noun.lower() == "quadport":
                result = powerbox.quadport_on(pegasus)
                dcp_result = "Powerbox quad port on."
                state.set_state_variable(subsystem_name, "result", dcp_result)
                
            elif noun.lower() == "adjustable":
                result = powerbox.adjport_on(pegasus)
                dcp_result = "Powerbox adjustable port on."
                state.set_state_variable(subsystem_name, "result", dcp_result)
                               
            else:
                output_message = "Error. Unknown device to activate."
                state.set_state_variable(subsystem_name, "result", output_message)
                logging.error(output_message)
                raise powerbox.PowerControllerError
            
        elif verb.lower()=="deactivate":
            
            if noun.lower() == "quadport":
                result = powerbox.quadport_off(pegasus)
                dcp_result = "Powerbox quad port off."
                state.set_state_variable(subsystem_name, "result", dcp_result)
                
            elif noun.lower() == "adjustable":
                result = powerbox.adjport_off(pegasus)
                dcp_result = "Powerbox adjustable port off."
                state.set_state_variable(subsystem_name, "result", dcp_result)
                               
            else:
                output_message = "Error. Unknown device to deactivate."
                state.set_state_variable(subsystem_name, "result", output_message)
                logging.error(output_message)
                raise powerbox.PowerControllerError
 
            
        elif verb.lower() == "report":
            result = powerbox.status(pegasus)
            (dummy,v,c,t,h,dp,qp,ao,d1p,d2p,ad,pwn,padj) = result[0].rstrip().split(":")
            dcp_result = {}
            dcp_result["InputVoltage[V]"] = float(v)
            dcp_result["CurrentBeingDrawn[A]"] = round(float(c)/65,3)
            dcp_result["Temperature[C]"] = float(t)
            dcp_result["Humidity[C]"] = float(h)
            dcp_result["Dewpoint[C]"] = float(dp)
            dcp_result["QuadportPowerStatus[0=Off,1=On]"] = int(qp)
            dcp_result["AdjustablePortPowerStatus[0=Off,1=On]"] = int(ao)
            dcp_result["DutyCycleDewAPort[0-255]"] = int(d1p)
            dcp_result["DutyCycleDewBPort[0-255]"] = int(d2p)
            dcp_result["AutodewStatus[0=Off,1=On]"] = int(ad)
            dcp_result["PowerWarningStatus[0=None,1=Alert]"] = int(pwn)
            dcp_result["AdjustablePortVoltage[V]"] = float(padj)
            state.set_state_variable(subsystem_name, "result", dcp_result)
            
        else:
            output_message = "Error. Unknown verb {}".format(verb)
            state.set_state_variable(subsystem_name, "result", output_message)
            logging.error(output_message)
            raise powerbox.PowerControllerError  
                   
    except:
        powerbox_busy = False
        dcp_result = "Error. Could not execute powerbox command."
        state.set_state_variable(subsystem_name, "result", dcp_result)   
        logging.error(dcp_result)
        pass
    
    powerbox_busy = False
    state.set_state_variable(subsystem_name,"busy", False)
    

# The main program defines the I/O loop. It waits for commands on a BSD Socket
# and relays these commands to the camera command thread.

def main():
    
    parser = argparse.ArgumentParser(
                        prog='dcp_powerbox_server',
                        description='Power server.',
                        epilog='Copyright 2023 - Team Dragonfly')
    parser.add_argument("-v", "--verbose", default=False, action="store_true", 
                        help="increase output verbosity (default = False)")
    parser.add_argument("-p", "--port", default="/dev/ttyUSB0", type=str, 
                        help="port that the power controller is on (default = /dev/ttyUSB0)")
    args = parser.parse_args()
    
    port = args.port
    
    global powerbox_busy
    global subsystem_name
    global dcp_result
    global recognized_verbs
    recognized_verbs = []
    powerbox_busy = False
        
    # Set IPC parameters
    subsystem_name = "powerbox"
    SOCK_FILE = "/tmp/{}.socket".format(subsystem_name)

    # Clean up old socket file
    if os.path.exists(SOCK_FILE):
        os.remove(SOCK_FILE)
  
    # Setup serial port
    with serial.Serial(port,
                        baudrate=9600,
                        parity=serial.PARITY_NONE,
                        bytesize=serial.EIGHTBITS,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1) as pegasus:
        time.sleep(0.1) #wait for serial port to open
        if pegasus.isOpen():
            
            # Set up the socket file for IPC communication.
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.bind(SOCK_FILE)
            s.listen(0)

            logging.info("Welcome to the Dragonfly Power Server.")
            logging.info("Listening for {} commands via file: {}".format(subsystem_name,SOCK_FILE))

            # This is the main loop, listening for commands.    
            while True:
                
                # Wait for data to come over the socket.
                try:
                    conn, addr = s.accept()
                
                except socket.timeout:
                    pass
        
                # Data received.
                logging.info("Connecton made by DCP client.")
                data = conn.recv(2048).decode()
                if not data: break  
                
                # Decode message
                message_dict = json.loads(data)
                logging.info("Received: {}".format(message_dict)) 
                verb, noun, arg1, arg2 = dcp.decode_message(message_dict)

                # Verbs we can process.
                recognized_verbs.append("quit")  
                recognized_verbs.append("activate")
                recognized_verbs.append("deactivate")
                recognized_verbs.append("report")    
            
                # One command ('quit') is somewhat special, as it does not
                # immediately interface with any hardware, so we can process 
                # it immediately.
                if verb.lower() == "quit":
                    info_string = "Server shutting down" + " ({})".format(subsystem_name)
                    conn.sendall(json.dumps(info_string).encode())
                    s.shutdown(socket.SHUT_RDWR)
                    s.close()
                    break

                # Process the message. The 'powerbox_busy' variable is global, and it is 
                # set in the command processing function in a separate thread.
                if powerbox_busy:
                    info_string = "Power controller is busy. Request ignored. Please try again in a few seconds."
                else:
                    if verb.lower() in recognized_verbs:
                        # start the command processing function running in the other thread
                        th.Thread(target=powerbox_command_thread, 
                                  args=(pegasus, verb, noun, arg1, arg2), 
                                  name='powerbox_command_thread', 
                                  daemon=True).start()
                        info_string = 'Command received by server.'
                    else:
                        info_string = 'Error. Command not recognized.'
                        state.set_state_variable(subsystem_name, "result", info_string)
                        logging.error(info_string)

                # Report back to the client.
                json_formatted_string = json.dumps(info_string)
                conn.sendall(json_formatted_string.encode())
                    
                # Close the connection to the client.
                conn.close()
  
if __name__ == '__main__':
    main()
