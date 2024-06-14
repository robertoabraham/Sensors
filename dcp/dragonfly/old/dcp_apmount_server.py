#!/home/dragonfly/miniforge3/envs/active_optics/bin/python
# -*- coding: utf-8 -*- 

import os
import threading as th
import logging
import json
import socket
import argparse
import time

from dragonfly import dcp as dcp
from dragonfly import apmount as apmount
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
apmount_busy = False
subsystem_name = "apmount"

# apmount operations are handled in a separate thread from the main I/O loop. The 
# operations thread is defined here.

def apmount_command_thread(gto, verb, noun, arg1, arg2):
    global apmount_busy
    global recognized_verbs
    apmount_busy = True
    state.set_state_variable(subsystem_name,"busy", True)    
        
    try:
        
        if verb.lower()=="connect":
            port = noun()
            try:
                dcp_result = gto.connect(port)
            except apmount.APMountError:
                dcp_result = f"Error. Could not connect to mount on port {port}."
            state.set_state_variable(subsystem_name, "result", dcp_result)
            
        elif verb.lower()=="disconnect":
            try:
                dcp_result = gto.disconnect()
            except apmount.APMountError:
                dcp_result = "Error. Could not disconnect to mount."
            state.set_state_variable(subsystem_name, "result", dcp_result)
            
        elif verb.lower()=="start":
            try:
                dcp_result = gto.start()
            except apmount.APMountError:
                dcp_result = "Error. Could not start tracking."
            state.set_state_variable(subsystem_name, "result", dcp_result)
            
        elif verb.lower()=="stop":
            try:
                dcp_result = gto.stop()
            except apmount.APMountError:
                dcp_result = "Error. Could not stop tracking."
            state.set_state_variable(subsystem_name, "result", dcp_result)
            
        elif verb.lower()=="park":
            try:
                dcp_result = gto.park()
            except apmount.APMountError:
                dcp_result = "Error. Could not park mount."
            state.set_state_variable(subsystem_name, "result", dcp_result)
            
        elif verb.lower()=="unpark":
            try:
                dcp_result = gto.unpark()
            except apmount.APMountError:
                dcp_result = "Error. Could not unpark mount."
            state.set_state_variable(subsystem_name, "result", dcp_result)
            
        elif verb.lower()=="panic":
            try:
                dcp_result = gto.panic()
            except apmount.APMountError:
                dcp_result = "Error. Could not stop motion."
            state.set_state_variable(subsystem_name, "result", dcp_result)
            
        elif verb.lower()=="status":
            try:
                dcp_result = gto.position()
                state.set_state_variable(subsystem_name, "is_connected", gto.status['is_connected'])           
                state.set_state_variable(subsystem_name, "is_slewing", gto.status['is_slewing'])
                state.set_state_variable(subsystem_name, "ra", gto.status['ra'])
                state.set_state_variable(subsystem_name, "dec", gto.status['dec'])
                state.set_state_variable(subsystem_name, "alt", gto.status['alt'])
                state.set_state_variable(subsystem_name, "az", gto.status['az'])
                state.set_state_variable(subsystem_name, "pier_side", gto.status['pier_side'])
                state.set_state_variable(subsystem_name, "latitude", gto.status['latitude'])
                state.set_state_variable(subsystem_name, "longitude", gto.status['longitude'])
                state.set_state_variable(subsystem_name, "gmt_offset", gto.status['gmt_offset'])
            except:
                dcp_result = "Error. Could not obtain information from the mount."
            state.set_state_variable(subsystem_name, "result", dcp_result)
            
        elif verb.lower()=="slew":
            ra = noun
            dec = arg1
            try:
                dcp_result = gto.slew(ra, dec, wait=True)
            except apmount.APMountError:
                dcp_result = "Error. Could not slew."
            state.set_state_variable(subsystem_name, "result", dcp_result)

        elif verb.lower()=="slew_to_target":     
            target = noun
            try:
                dcp_result = gto.slew_to_target(target, wait=True)
            except apmount.APMountError:
                dcp_result = "Error. Could not slew to target."
            state.set_state_variable(subsystem_name, "result", dcp_result)
            
        elif verb.lower()=="jog":
            amount = noun
            direction = arg1.lower()
            try:
                dcp_result = gto.jog(amount, direction, wait=True)
            except apmount.APMountError:
                dcp_result = "Error. Could not jog."
            state.set_state_variable(subsystem_name, "result", dcp_result)                  
            
        elif verb.lower()=="sync":
            ra = noun
            dec = arg1
            try:
                dcp_result = gto.sync(ra, dec, wait=True)
            except apmount.APMountError:
                dcp_result = "Error. Could not sync."
            state.set_state_variable(subsystem_name, "result", dcp_result)            
            
        elif verb.lower()=="sync_to_target":
            target = noun
            try:
                dcp_result = gto.sync_to_target(target, wait=True)
            except apmount.APMountError:
                dcp_result = "Error. Could not sync to target."
            state.set_state_variable(subsystem_name, "result", dcp_result)
            
        elif verb.lower()=="sync_to_image":
            filename = noun
            try:
                dcp_result = gto.sync_to_image(filename, wait=True)
            except apmount.APMountError:
                dcp_result = "Error. Could not sync to image."
            state.set_state_variable(subsystem_name, "result", dcp_result)
 
        else:
            output_message = "Error. Unknown verb {}".format(verb)
            state.set_state_variable(subsystem_name, "result", output_message)
            logging.error(output_message)
            raise apmount.PowerControllerError  

    except:
        apmount_busy = False
        dcp_result = "Error. Could not execute apmount command."
        state.set_state_variable(subsystem_name, "result", dcp_result)   
        logging.error(dcp_result)
        pass
    
    apmount_busy = False
    state.set_state_variable(subsystem_name,"busy", False)

# The main program defines the I/O loop. It waits for commands on a BSD Socket
# and relays these commands to the camera command thread.

def main():
    
    parser = argparse.ArgumentParser(
                        prog='dcp_apmount_server',
                        description='Astro-Physics mount server.',
                        epilog='Copyright 2023 - Team Dragonfly')
    parser.add_argument("-v", "--verbose", default=False, action="store_true", 
                        help="increase output verbosity (default = False)")
    parser.add_argument("-p", "--port", default="/dev/ttyUSB0", type=str, 
                        help="port that the mount is on (default = /dev/ttyUSB1)")
    parser.add_argument("-g", "--graphics", default=False, type=str, 
                        help="Display sky position graphics (default = False)")
    args = parser.parse_args()
    
    port = args.port
    
    global apmount_busy
    global subsystem_name
    global dcp_result
    global recognized_verbs
    recognized_verbs = []
    apmount_busy = False
        
    # Set IPC parameters
    subsystem_name = "apmount"
    SOCK_FILE = "/tmp/{}.socket".format(subsystem_name)

    # Clean up old socket file
    if os.path.exists(SOCK_FILE):
        os.remove(SOCK_FILE)

    # Setup serial port
    logging.info("Opening serial port.") 
        
    gto = apmount.GTOControlBox(port=port)
        
    try:
        
        # Initialize the mount
        logging.info("Connecting to the mount.") 
        result = gto.connect()
        logging.info("Received: {}".format(result)) 
        
        # Set up the socket file for IPC communication.
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind(SOCK_FILE)
        s.listen(0)

        logging.info("Welcome to the Dragonfly Astro-Physics GTO Mount Server.")
        logging.info("Listening for {} commands via file: {}".format(subsystem_name,SOCK_FILE))

        # This is the main loop, listening for commands.    
        while True:
            
            # Wait for data to come over the socket.
            try:
                conn, addr = s.accept()
            
            except socket.timeout:
                pass
    
            # Data received.
            logging.info("Connection made by DCP client.")
            data = conn.recv(2048).decode()
            if not data: break  
            
            # Decode message
            message_dict = json.loads(data)
            logging.info("Received: {}".format(message_dict)) 
            verb, noun, arg1, arg2 = dcp.decode_message(message_dict)

            # Verbs we can process.
            recognized_verbs.append("quit")
            recognized_verbs.append("connect")
            recognized_verbs.append("disconnect")
            recognized_verbs.append("status") 
            recognized_verbs.append("slew_to_target")
            recognized_verbs.append("slew")
            recognized_verbs.append("sync_to_target")
            recognized_verbs.append("sync_to_image")
            recognized_verbs.append("sync")
            recognized_verbs.append("jog")
            recognized_verbs.append("start")
            recognized_verbs.append("stop")
            recognized_verbs.append("panic")
            recognized_verbs.append("park")
            recognized_verbs.append("unpark")
        
            # One command ('quit') is somewhat special, as it does not
            # immediately interface with any hardware, so we can process 
            # it immediately.
            if verb.lower() == "quit":
                info_string = "Server shutting down" + " ({})".format(subsystem_name)
                conn.sendall(json.dumps(info_string).encode())
                s.shutdown(socket.SHUT_RDWR)
                s.close()
                break

            # Process the message. The 'apmount_busy' variable is global, and it is 
            # set in the command processing function in a separate thread.
            if apmount_busy:
                info_string = "AP mount is busy. Request ignored. Please try again in a few seconds."
            else:
                if verb.lower() in recognized_verbs:
                    # start the command processing function running in the other thread
                    th.Thread(target=apmount_command_thread, 
                                args=(gto, verb, noun, arg1, arg2), 
                                name='apmount_command_thread', 
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
            
    except:
        
        raise apmount.APMountError
  
if __name__ == '__main__':
    main()
