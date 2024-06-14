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
from dragonfly import fastlens as lens
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
lens_busy = False
subsystem_name = "fastlens"

# Lens operations are handled in a separate thread from the main I/O loop. The 
# operations thread is defined here.

def lens_command_thread(arduino, verb, noun, arg1, arg2):
    global lens_busy
    global recognized_verbs
    lens_busy = True
    state.set_state_variable(subsystem_name,"busy", True)    
        
    try:
               
        if verb.lower() == "check":
            result = lens.check_lens_presence(arduino)
            if 'Lens is connected!' in result:
                output_message = "Success. Lens found."
                logging.info(output_message)
                state.set_state_variable(subsystem_name, "present", True)
            else:
                output_message = "Error. Lens not found."
                logging.info(output_message)
                state.set_state_variable(subsystem_name, "present", False)
            state.set_state_variable(subsystem_name, "result", output_message)

        elif verb == "unlock":
            result = lens.activate_image_stabilization(arduino)
            if not ('IS did not unlock' in result):
                state.set_state_variable(subsystem_name, "locked", False)
                output_message = "Success. IS unit unlocked."
            else:
                output_message = "Error. IS Unit returned unexpected opcode."
            state.set_state_variable(subsystem_name, "result", output_message)
 
        elif verb == "lock":
            lens.set_is_x_position(arduino, 0)
            lens.set_is_y_position(arduino, 0)
            x,y =  lens.get_is_position(arduino)
            state.set_state_variable(subsystem_name,"x", x)
            state.set_state_variable(subsystem_name,"y", y)
            if (abs(x) > 5) or (abs(y) > 5):
                output_message = "Error. Lens could not be homed."
            else:
                result = lens.deactivate_image_stabilization(arduino)
                if ('SPI received: C' in result) or ('SPI received: 4' in result):
                    state.set_state_variable(subsystem_name, "locked", True)
                    output_message = "Success. IS unit set to (X,Y)=(0,0) and locked."
                else:
                    output_message = "Error. IS Unit returned unexpected opcode."
            state.set_state_variable(subsystem_name, "result", output_message)

        elif verb == "initialize":
            # Clear out a variable that gets reset by the initialization process. We
            # do this as we will compare its value to a known value later and want to
            # make sure this value is correct.
            state.set_state_variable(subsystem_name, "z_max", 0)
            result = lens.initialize(arduino, verbose=False)
            expected_position = 10000
            current_position =  int(lens.get_focus_position(arduino))
            maximum_position = state.get_state_variable(subsystem_name, "z_max")
            if ((abs(current_position - expected_position) <= 5) and 
                (maximum_position > 20000 and maximum_position < 25000)):
                state.set_state_variable(subsystem_name, "initialized", True)
                output_message = "Success. Lens is initialized."  
            else:
                state.set_state_variable(subsystem_name, "initialized", False)
                output_message = "Error. Lens initialization returned unexpected opcode." 
            state.set_state_variable(subsystem_name, "result", output_message)

        elif verb == "goto":
                        
            if noun.lower() == "z":
                
                # Adjust lens focus.
                desired_position = int(arg1)
                result = lens.set_focus_position(arduino, desired_position)
                m1 = 'SPI received: 44'             # An acceptable message.
                m2 = 'Cannot have quantity of 0'    # Also an acceptble message.
                if (m1 in result) or (m2 in result):                    
                    current_position =  lens.get_focus_position(arduino)
                    state.set_state_variable(subsystem_name, "z", current_position)
                    if abs(current_position - desired_position) <= 5:
                        output_message = "Success. Lens currently at: {}".format(current_position)
                        logging.info(output_message)
                    else:
                        output_message = "Error. Lens currently at: {}".format(current_position)
                        logging.error(output_message)
                else:
                    output_message = "Error. Could not communicate with lens."
                    logging.error(output_message)
                state.set_state_variable(subsystem_name, "result", output_message)

            elif noun.lower() == "x":
                
                # Is the lens unlocked?
                is_locked = state.get_state_variable(subsystem_name,"locked")
                if is_locked:
                    logging.error("Error. Lens must be unlocked before IS commands are sent.")
                    raise lens.CanonLensISError
                         
                # Adjust lens X-displacement.
                desired_position = int(arg1)
                result = lens.set_is_x_position(arduino, desired_position)
                ok_message = 'SPI received: 72'    # The expected message.
                if (ok_message in result):
                    x,y =  lens.get_is_position(arduino)
                    state.set_state_variable(subsystem_name,"x", x)
                    if abs(desired_position - x) <= 5:
                        output_message = "Success. Lens IS unit currently at X: {} Desired position: {}".format(x, desired_position)
                    else:
                        output_message = "Error. Lens IS unit currently at X: {} Desired position: {}".format(x, desired_position)  
                else:
                    output_message = "Error. Lens IS usnit returned unexpected opcode." 
                    
                state.set_state_variable(subsystem_name, "result", output_message)

                    
            elif noun.lower() == "y":
                
                # Is the lens unlocked?
                is_locked = state.get_state_variable(subsystem_name,"locked")
                if is_locked:
                    logging.error("Error. Lens must be unlocked before IS commands are sent.")
                    raise lens.CanonLensISError
                         
                # Adjust lens Y-displacement.
                desired_position = int(arg1)
                result = lens.set_is_y_position(arduino, desired_position)
                ok_message = 'SPI received: 72'    # The expected message.
                if (ok_message in result):
                    x,y =  lens.get_is_position(arduino)
                    state.set_state_variable(subsystem_name,"y", y)
                    if abs(desired_position - y) <= 5:
                        output_message = "Success. Lens IS unit currently at Y: {} Desired position: {}".format(y, desired_position)
                    else:
                        output_message = "Error. Lens IS unit currently at Y: {} Desired position: {}".format(y, desired_position)  
                else:
                    output_message = "Error. Lens IS usnit returned unexpected opcode." 
                    
                state.set_state_variable(subsystem_name, "result", output_message)

            else:
                message = "Error. Goto noun must be one of x, y, or z."
                logging.error(message)
                state.set_state_variable(subsystem_name, "result", message)
                raise lens.CanonLensError
                        
        else:
            output_message = "Error. Unknown verb {}".format(verb)
            logging.info(output_message)
            raise lens.PowerControllerError  
                   
    except:
        lens_busy = False
        dcp_result = "Error executing lens command."
        logging.error(dcp_result)
        state.set_state_variable(subsystem_name, "result", dcp_result)   
        pass
    
    lens_busy = False
    state.set_state_variable(subsystem_name, "busy", False)
    

# The main program defines the I/O loop. It waits for commands on a BSD Socket
# and relays these commands to the camera command thread.

def main():
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", default=False, action="store_true", 
                        help="increase output verbosity (default = False)")
    parser.add_argument("-p", "--port", default="/dev/ttyACM0", 
                        help="port name (default = /dev/ttyACM0)")
    args = parser.parse_args()
    
    serial_port = args.port
        
    global lens_busy
    global subsystem_name
    global dcp_result
    global recognized_verbs
    recognized_verbs = []
    lens_busy = False
        
    # Set IPC parameters
    SOCK_FILE = "/tmp/{}.socket".format(subsystem_name)

    # Clean up old socket file
    if os.path.exists(SOCK_FILE):
        os.remove(SOCK_FILE)
  
    # Setup serial port
    with serial.Serial(serial_port,
                       baudrate=9600,
                       parity=serial.PARITY_NONE,
                       bytesize=serial.EIGHTBITS,
                       stopbits=serial.STOPBITS_ONE,
                       timeout=1) as arduino:
        time.sleep(0.1) #wait for serial port to open
        if arduino.isOpen():
            
            # Set up the socket file for IPC communication.
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.bind(SOCK_FILE)
            s.listen(0)

            logging.info("Welcome to the Experimental Dragonfly Fast Lens Server.")
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

                # Verbs we can process. Dealing with these gets spun off to another thread.
                recognized_verbs.append("check")
                recognized_verbs.append("goto")
                recognized_verbs.append("unlock")
                recognized_verbs.append("lock")    
                recognized_verbs.append("initialize")
                
                # Three additional commands ('quit', 'get' and 'set') are somewhat special, as they
                # don't immediately interface with any hardware, so we will process them immediately
                # without spinning anything off to another thread.
                if verb == "quit":
                    info_string = "Server shutting down" + " ({})".format(subsystem_name)
                    conn.sendall(json.dumps(info_string).encode())
                    s.shutdown(socket.SHUT_RDWR)
                    s.close()
                    break
                
                if verb == "get":
                    try:
                        info_json = json.dumps(state.get_state_variable(subsystem_name,noun))
                    except:
                        info_json = json.dumps("Error. Could not retrieve value for keyword {}".format(noun))
                    conn.sendall(info_json.encode())
                    conn.close()
                    continue
                
                if verb == "set":
                    try:
                        state.set_state_variable(subsystem_name,noun,arg1)
                        message = "Set keyword '{}' to {}".format(noun,arg1)
                        logging.info(message)
                        info_json = json.dumps(message)
                    except:
                        info_json = json.dumps("Error. Could not set keyword")
                    conn.sendall(info_json.encode())
                    conn.close()
                    continue

                # Process the message. The 'lens_busy' variable is global, and it is 
                # set in the command processing function in a separate thread.
                if lens_busy:
                    info_string = "Error. Power controller is busy. Request ignored. Please try again in a few seconds."
                else:
                    if verb.lower() in recognized_verbs:
                        # start the command processing function running in the other thread
                        th.Thread(target=lens_command_thread, 
                                  args=(arduino, verb, noun, arg1, arg2), 
                                  name='lens_command_thread', 
                                  daemon=True).start()
                        info_string = "Command received by server."
                    else:
                        info_string = "Error. Command not recognized."
                        logging.error(info_string)

                # Report back to the client.
                json_formatted_string = json.dumps(info_string)
                conn.sendall(json_formatted_string.encode())
                    
                # Close the connection to the client.
                conn.close()
  
if __name__ == '__main__':
    main()
