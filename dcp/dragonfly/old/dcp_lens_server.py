#!/home/dragonfly/miniforge3/envs/active_optics/bin/python
# -*- coding: utf-8 -*- 

import os
import sys
import threading as th
import logging
import json
import socket
import argparse

from dragonfly import dcp as dcp
from dragonfly import state as state
from dragonfly import lens as lens
from dragonfly import utility as utility

# Setup logging to write to both the screen and a log file.
logging.basicConfig(
   level=logging.INFO,
   format="%(asctime)s [%(levelname)s] %(message)s",
   handlers=[
       logging.FileHandler("/home/dragonfly/dragonfly-arm/active_optics/dashboard/log.txt"),
       logging.StreamHandler()
   ])

lens_busy = False
subsystem_name = "lens"
dcp_result = {}

# Lens operations are handled in a separate thread from the main I/O loop. The lens
# operations thread is defined here.

def lens_command_thread(verb, noun, arg1, arg2):
    global lens_busy
    global dcp_result
    lens_busy = True
    state.set_state_variable(subsystem_name,"busy", True)    
        
    # Execute commands here.
    result = ""
    try:
            
        if verb == "check":
            state.clear_output_streams(subsystem_name)
            result = lens.check_lens_presence()
            result_line = utility.find_line_in_subprocess_stdout(result, 'Result')
            if 'Lens is connected!' in result_line:
                output_message = "Success. Lens found."
                logging.info(output_message)
                state.set_state_variable(subsystem_name, "present", True)
            else:
                output_message = "Error. Lens not found."
                logging.info(output_message)
                state.set_state_variable(subsystem_name, "present", False)
            dcp.handle_subprocess_result(subsystem_name, result, 
                                         output_message,
                                         "Error. Could not communicate with lens.")   
 
        elif verb == "unlock":
            state.clear_output_streams(subsystem_name)
            result = lens.activate_image_stabilization()
            if not ('IS did not unlock' in result.stdout.decode()):
                state.set_state_variable(subsystem_name, "locked", False)
                dcp.handle_subprocess_result(subsystem_name, result, 
                                         "Success. IS unit unlocked.",
                                         "Error. Could not communicate with lens.")   
            else:
                dcp.handle_subprocess_result(subsystem_name, result, 
                                         "Error. IS Unit returned unexpected opcode.",
                                         "Error. Could not communicate with lens.")   

        elif verb == "lock":
            state.clear_output_streams(subsystem_name)
            result = lens.set_is_x_position(0)
            state.set_state_variable(subsystem_name,"x", 0)
            result = lens.set_is_y_position(0)
            state.set_state_variable(subsystem_name,"y", 0)
            result = lens.deactivate_image_stabilization()
            if 'SPI received: C' in result.stdout.decode() or 'SPI received: 4' in result.stdout.decode():
                state.set_state_variable(subsystem_name, "locked", True)
                dcp.handle_subprocess_result(subsystem_name, result, 
                                         "Success. IS unit set to (X,Y)=(0,0) and locked.",
                                         "Error. Could not communicate with lens.")   
            else:
                dcp.handle_subprocess_result(subsystem_name, result, 
                                         "Error. IS unit unit returned unexpected opcode.",
                                         "Error. Could not communicate with lens.")   
                
        elif verb == "initialize":
            state.clear_output_streams(subsystem_name)
            result = lens.initialize()
            expected_position = 10000
            current_position =  int(lens.get_focus_position())
            if abs(current_position - expected_position) <= 5:
                state.set_state_variable(subsystem_name, "initialized", True)
                dcp.handle_subprocess_result(subsystem_name, result['move_middle'], 
                                         "Success. Lens is initialized.",
                                         "Error. Could not initialize lens.")   
            else:
                dcp.handle_subprocess_result(subsystem_name, result['move_middle'], 
                                         "Error. Lens initialization returned unexpected opcode.",
                                         "Error. Could not communicate with lens.")  
                
        elif verb == "goto":
            
            state.clear_output_streams(subsystem_name)
            
            if noun.lower() == "z":
                # Adjust lens focus.
                desired_position = int(arg1)
                result = lens.set_focus_position(desired_position)
                m1 = 'SPI received: 44'             # An acceptable message.
                m2 = 'Cannot have quantity of 0'    # Also an acceptble message.
                if ( m1 in result.stdout.decode()) or ( m2 in result.stdout.decode()):
                    current_position =  lens.get_focus_position()
                    state.set_state_variable(subsystem_name,"z", current_position)
                    if abs(current_position - desired_position) <= 5:
                        message = "Success. Lens currently at: {}".format(current_position)
                    else:
                        message = "Error. Lens currently at: {}".format(current_position)
                    dcp.handle_subprocess_result(subsystem_name, result, 
                                            message,
                                            "Error. Could not communicate with lens.")   
                else:
                    dcp.handle_subprocess_result(subsystem_name, result, 
                                            "Error. Lens focus command returned unexpected opcode.",
                                            "Error. Could not communicate with lens.")   

            elif noun.lower() == "x":
                
                # Is the lens unlocked?
                is_locked = state.get_state_variable(subsystem_name,"locked")
                if is_locked:
                    logging.error("Error. Lens must be unlocked before IS commands are sent.")
                    raise lens.CanonLensISError
                
                # Adjust lens X-displacement.
                desired_position = int(arg1)
                result = lens.set_is_x_position(desired_position)
                ok_message = 'Result: SPI received: 72'    # An acceptable message.
                if (ok_message in result.stdout.decode()):
                    x,y =  lens.get_is_position()
                    state.set_state_variable(subsystem_name,"x", x)
                    if abs(desired_position - x) <= 5:
                        message = "Success. Lens IS unit currently at X: {} Desired position: {}".format(x, desired_position)
                    else:
                        message = "Error. Lens IS unit currently at X: {} Desired position: {}".format(x, desired_position)
                    dcp.handle_subprocess_result(subsystem_name, result, 
                                            message,
                                            "Error. Could not communicate with lens.")   
                else:
                    dcp.handle_subprocess_result(subsystem_name, result, 
                                            "Error. Lens IS unit command returned unexpected opcode.",
                                            "Error. Could not communicate with lens.")  
                    
            elif noun.lower() == "y":
                
                # Is the lens unlocked?
                is_locked = state.get_state_variable(subsystem_name,"locked")
                if is_locked:
                    logging.error("Error. Lens must be unlocked before IS commands are sent.")
                    raise lens.CanonLensISError
                
                # Adjust lens Y-displacement.
                desired_position = int(arg1)
                result = lens.set_is_y_position(desired_position)
                ok_message = 'Result: SPI received: 72'    # An acceptable message.
                if (ok_message in result.stdout.decode()):
                    x,y =  lens.get_is_position()
                    state.set_state_variable(subsystem_name,"y", y)
                    if abs(desired_position - y) <= 5:
                        message = "Success. Lens IS unit currently at Y: {} Desired position: {}".format(y, desired_position)
                    else:
                        message = "Error. Lens IS unit currently at Y: {} Desired position: {}".format(y, desired_position)
                    dcp.handle_subprocess_result(subsystem_name, result, 
                                            message,
                                            "Error. Could not communicate with lens.")   
                else:
                    dcp.handle_subprocess_result(subsystem_name, result, 
                                            "Error. Lens IS unit command returned unexpected opcode.",
                                            "Error. Could not communicate with lens.") 
            
            else:
                output_message = "Error. Goto noun must be one of x, y, or z."
                logging.info(output_message)
                raise lens.CanonLensError
                    
    except:
        lens_busy = False
        process_data = {}
        process_data["stdout"] = b""
        process_data["stderr"] = b"Error. Lens error."
        process_data["returncode"] = 1
        dcp.store_and_log_subprocess_result(subsystem_name, process_data)
        logging.error("Error executing lens command.")
        output_message = "Lens error."
        dcp_result = dcp.organize_result(
            output_message,
            subprocess_result=None
        )
        state.set_state_variable(subsystem_name,"result",dcp_result)
        pass
    
    lens_busy = False
    state.set_state_variable(subsystem_name,"busy", False)
    

# The main program defines the I/O loop. It waits for commands on a BSD Socket
# and relays these commands to the camera command thread.
    
def main():
    
    parser = argparse.ArgumentParser(
                        prog='dcp_lens_server',
                        description='Canon lens server.',
                        epilog='Copyright 2023 - Team Dragonfly')

    args = parser.parse_args()
    
    global lens
    global subsystem_name
    lens_busy = False
    
    # Check if the lens is present.
    result = lens.check_lens_presence()
    try:
        result_line = utility.find_line_in_subprocess_stdout(result, 'Result')
        if 'Lens is connected!' in result_line:
            logging.info("Lens found.")
            state.set_state_variable(subsystem_name, "present", True)
        else:
            state.set_state_variable(subsystem_name, "present", False)
            logging.error("Error. Lens not found.")
            sys.exit()
    except:
        raise lens.CanonLensError
        
    # Set IPC parameters
    SOCK_FILE = "/tmp/{}.socket".format(subsystem_name)

    # Setup socket
    if os.path.exists(SOCK_FILE):
        os.remove(SOCK_FILE)

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(SOCK_FILE)
    s.listen(0)

    logging.info("Welcome to the Dragonfly Canon Lens Server.")
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

        # Three commands ('quit', 'get' and 'set') are somewhat special, as they do not
        # immediately interface with any hardware, so we can process them immediately.
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
        
        recognized_verbs = []
        recognized_verbs.append("check")
        recognized_verbs.append("lock")
        recognized_verbs.append("unlock")
        recognized_verbs.append("goto")
        recognized_verbs.append("initialize")


        # Process the message. The 'lens_busy' variable is global, and it is set in the
        # command processing function in a separate thread.
        if lens_busy:
            info_string = "Error. Camera is busy. Request ignored. ETA for camera to be free: XXX seconds."
        else:
            if verb in recognized_verbs:
                # start the command processing function running in the other thread
                th.Thread(target=lens_command_thread, args=(verb, noun, arg1, arg2), 
                          name='lens_command_thread', daemon=True).start()
                info_string = "Command received by server."
            else:
                info_string = "Error. Command not recognized."
                logging.info(info_string)

        
        # Report back to the client.
        json_formatted_string = json.dumps(info_string)
        conn.sendall(json_formatted_string.encode())
            
        # Close the connection to the client.
        conn.close()

if __name__ == '__main__':
    main()
