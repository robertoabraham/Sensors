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
from dragonfly import camera as camera
from dragonfly import utility as utility

# Setup logging to write to both the screen and a log file.
logging.basicConfig(
   level=logging.INFO,
   format="%(asctime)s [%(levelname)s] %(message)s",
   handlers=[
       logging.FileHandler("/home/dragonfly/dragonfly-arm/active_optics/dashboard/log.txt"),
       logging.StreamHandler()
   ])

camera_busy = False
camera_name = ""
dcp_result = {}

# Camera operations are handled in a separate thread from the main I/O loop. The camera
# operations thread is defined here.

def aluma_command_thread(verb, noun, arg1, arg2):
    global camera_busy
    global dcp_result
    camera_busy = True
    state.set_state_variable(camera_name,"busy", True)    
    
    # Execute commands here.
    result = ""
    try:
                    
        if verb == "expose":
            state.set_state_variable(camera_name,"result", None)   
            state.clear_output_streams(camera_name)
            camera_number = state.get_state_variable(camera_name,"camera_number")
            if noun == None:
                exptime = state.get_state_variable(camera_name,"exptime")
            else:
                exptime = float(noun)
                state.set_state_variable(camera_name,"exptime",exptime)
            next_filename = state.get_state_variable(camera_name,"next_filename")
            savedir = state.get_state_variable(camera_name,"savedir")
            include_overscan = state.get_state_variable(camera_name,"include_overscan")
            imtype = state.get_state_variable(camera_name,"imtype")
            state.set_state_variable(camera_name,"exposing", True)
            result = camera.expose(camera_number, exptime, imtype, next_filename, savedir, include_overscan)
            state.set_state_variable(camera_name, "exposing", False)
            dcp.handle_subprocess_result(camera_name, result, 
                                         "Success. Image obtained.",
                                         "Error. Could not obtain an image.",
                                         add_details=True)
            try:
                if result.returncode == 0:
                    last_filename = result.stdout.decode().strip()
                    state.set_state_variable(camera_name, "last_filename", last_filename)
                    logging.info("Recording last_filename variable as {}".format(last_filename))
            except:
                logging.info("Error storing last_filename variable.")
                pass
  
            
        elif verb == "list":
            state.clear_output_streams(camera_name)
            result = camera.list()
            dcp.handle_subprocess_result(camera_name, result, 
                                         "Success. Cameras enumerated.",
                                         "Error. Could not enumerate cameras.")    
            
        elif verb == "enable_cooling":
            if noun is None or noun == "":
                setpoint = str(state.get_state_variable(camera_name,"setpoint"))
            else:
                setpoint = noun
            state.clear_output_streams(camera_name)
            result = camera.enable(setpoint)
            dcp.handle_subprocess_result(camera_name, result, 
                                         "Success. Cooling enabled.",
                                         "Error. Cooling could not be started.")            
                        
        elif verb == "disable_cooling":
            state.clear_output_streams(camera_name)
            result = camera.disable()
            dcp.handle_subprocess_result(camera_name, result, 
                                         "Success. Cooling disabled.",
                                         "Error. Cooling could not be disabled.")    
            
        elif verb == "get_temperature":
            state.clear_output_streams(camera_name)
            result = camera.get_temperature()
            dcp.handle_subprocess_result(camera_name, result, 
                                         "Success. Temperature obtained.",
                                         "Error. Could not obtain temperature.")  
            
    except:
        camera_busy = False
        process_data = {}
        process_data["stdout"] = b""
        process_data["stderr"] = b"Error. Camera error."
        process_data["returncode"] = 1
        dcp.store_and_log_subprocess_result(camera_name, process_data)
        logging.error("Error executing camera command.")
        output_message = "Camera error."
        dcp_result = dcp.organize_result(
            output_message,
            subprocess_result=None
        )
        state.set_state_variable(camera_name,"result",dcp_result)
        pass
    
    camera_busy = False
    state.set_state_variable(camera_name,"busy", False)
    

# The main program defines the I/O loop. It waits for commands on a BSD Socket
# and relays these commands to the camera command thread.
    
def main():
    
    parser = argparse.ArgumentParser(
                        prog='dcp_camera_server',
                        description='SBIG CCD/CMOS Camera server.',
                        epilog='Copyright 2023 - Team Dragonfly')

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--camera", default="aluma", help="Name of camera (starchaser or aluma). (default=aluma)")
    args = parser.parse_args()
    
    global camera_busy
    global camera_name
    camera_busy = False
    
    # Locate the appropriate camera
    camera_name = args.camera.lower()
    if (camera_name != "aluma") and (camera_name != "starchaser"):
        logging.error("{} is not a known camera name".format(camera_name))
        sys.exit()
    
    camnum = camera.find_camera_number(camera_name)
    if (camnum < 0):
        logging.error("{} not found".format(camera_name))
        sys.exit()
        
    state.set_state_variable(camera_name, "camera_number", camnum)

    # IPC parameters
    SOCK_FILE = "/tmp/{}.socket".format(camera_name)

    # Setup socket
    if os.path.exists(SOCK_FILE):
        os.remove(SOCK_FILE)

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(SOCK_FILE)
    s.listen(0)

    logging.info("Welcome to the Dragonfly SBIG Camera Server.")
    logging.info("Listening for {} commands via file: {}".format(camera_name,SOCK_FILE))

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
            info_string = "Server shutting down" + " ({})".format(camera_name)
            conn.sendall(json.dumps(info_string).encode())
            s.shutdown(socket.SHUT_RDWR)
            s.close()
            break
        
        if verb == "get":
            try:
                info_json = json.dumps(state.get_state_variable(camera_name,noun))
            except:
                info_json = json.dumps("Error. Could not retrieve value for keyword {}".format(noun))
            conn.sendall(info_json.encode())
            conn.close()
            continue
        
        if verb == "set":
            try:
                state.set_state_variable(camera_name,noun,arg1)
                message = "Set keyword '{}' to {}".format(noun,arg1)
                logging.info(message)
                info_json = json.dumps(message)
            except:
                info_json = json.dumps("Error. Could not set keyword")
            conn.sendall(info_json.encode())
            conn.close()
            continue
        
        recognized_verbs = []
        recognized_verbs.append("expose")
        recognized_verbs.append("set")
        recognized_verbs.append("list")
        recognized_verbs.append("get_temperature")
        recognized_verbs.append("disable_cooling")
        recognized_verbs.append("enable_cooling")

        # Process the message. The 'camera_busy' variable is global, and it is set in the
        # command processing function in a separate thread.
        if camera_busy:
            info_string = "Error. Camera is busy. Request ignored. ETA for camera to be free: XXX seconds."
        elif verb in recognized_verbs:
                # start the command processing function running in the other thread
                th.Thread(target=aluma_command_thread, args=(verb, noun, arg1, arg2), 
                          name='aluma_command_thread', daemon=True).start()
                info_string = "Command received by server."
        else:
            info_string = "Error. Command not recognized."
        
        # Report back to the client.
        json_formatted_string = json.dumps(info_string)
        conn.sendall(json_formatted_string.encode())
            
        # Close the connection to the client.
        conn.close()

if __name__ == '__main__':
    main()
