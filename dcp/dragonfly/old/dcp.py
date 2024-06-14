# Commands useful for the Dragonfly Communication Protocol

import logging
import subprocess
import json
import socket
import os
import time

from dragonfly import state

log = logging.getLogger('team_dragonfly')
log.addHandler(logging.NullHandler())

class DCPServerError(Exception):
    """Exception raised because of an error condition reported by a DCP server.
    
    Attributes:
        server_message -- information sent by the server
    """
    def __init__(self, server_message="Error resulting from DCP communication"):
        self.server_message = server_message
        super().__init__(self.server_message)

def send(server, verb, noun=None, arg1=None, arg2=None, asynchronous=False, json_string=False):
    """Sends a message to a DCP server
    """
    
    data_to_send = {
    "verb": verb,
    "noun": noun,
    "arg1": arg1,
    "arg2": arg2
    }

    # Serialize the command dictionary as a JSON string  
    json_object = json.dumps(data_to_send) 

    # Communication is done using BSD socket files named after the server.
    SOCK_FILE = "/tmp/{}.socket".format(server)
    
    # Init socket object
    if not os.path.exists(SOCK_FILE):
        error_message = f"Error. File {SOCK_FILE} doesn't exist"
        raise DCPServerError(error_message)

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(SOCK_FILE)
    s.sendall(json_object.encode())

    # Wait for response
    data = s.recv(2048)
    s.close()
    
    # Throw an exception if the server immediately reports an error.
    if data.decode().startswith('Error'):
        raise DCPServerError(data.decode())
    
    # We have just sent a message to a hardware device, and it has sent a message
    # back indicating that it received the message.  The default action now is to
    # poll the device to see if it is busy and wait until it signals that it isn't.
    # However, if the user has set the --async flag then we just bail out here and
    # it will be up the user to ask the check later to see if the device is no
    # longer busy.

    # Because it doesn't make sense to wait for "set" or "get" commands (these
    # don't ever start long-running processes on the server) we don't wait for
    # answers from those verbs. We also don't wait for a respose to the "quit"
    # command, as that likewise doesn't make sense.
    #
    # To try to mitigate against the awkward situation where we try to to read the
    # state file at the same file as the server tries to write to it, we mainly
    # rely on lockfiles. Out of a sense of paranoia, we also try three times to
    # access the state file (with a short pause between attempts) before giving up.

    if (asynchronous != True and verb != "get" and verb != "set" and verb != "quit"):
        time.sleep(0.5)
        while(True):
            state_unknown = True
            nattempt = 0
            nattempt_max = 3
            is_busy = False

            # Try up to three times to get the state.
            while (state_unknown == True) and (nattempt < nattempt_max):
                try:
                    is_busy = state.get_state_variable(server, "busy")
                    state_unknown = False
                except:
                    print("Could not get state. Trying again.")
                    nattempt = nattempt + 1
                    time.sleep(1)
                
            if is_busy == True:
                time.sleep(1)
            else:
                # This result is returned as a Python dictionary! Needs conversion
                # to JSON to be in the same format as the result returned by
                # the socket command.
                output = state.get_state_variable(server, "result")
                output = json.dumps(output)
                break
    else:
        
        # Running asynchronously. Data is received as a byte-encoded JSON string.
        output = data.decode()
        
    # Optionally decode the string to turn it into a Python dictionary.
    if not json_string:
        output = json.loads(output)
        
    if isinstance(output, str):
        if output.startswith('Error'):
            raise DCPServerError(output)
        
    if isinstance(output, dict):
        if 'stream' in output:
            if output['stream'] == None:
                error_message = "Error running external program. Server sent:\n" + str(output)
                raise DCPServerError(error_message)                    
            if 'returncode' in output['stream']:
                if output['stream']['returncode'] != 0:
                    error_message = "Error running external program. Server sent:\n" + str(output)
                    raise DCPServerError(error_message)

    return(output)
        
def decode_message(message_dict):
    """Converts a message dictionary into a list of command elements (verb, noun, arg1, arg2)"""
    if message_dict["verb"] is not None:
        verb = message_dict["verb"].lower()
    else:
        verb = None
    if message_dict["noun"] is not None:
        noun = message_dict["noun"]
        if isinstance(noun, str):
            noun = noun.lower()
    else:
        noun = None
    if message_dict["arg1"] is not None:
        arg1 = message_dict["arg1"]
        if isinstance(arg1, str):
            arg1 = arg1.lower()
    else:
        arg1 = None
    if message_dict["arg2"] is not None:
        arg2 = message_dict["arg2"]
        if isinstance(arg2, str):
            arg2 = arg2.lower()
    else:
        arg2 = None
    return(verb, noun, arg1, arg2)

def store_and_log_subprocess_result(subsystem, result):
    """Store (in a state file) and report (to a log file) the outcome of calling a subprocess."""
    if type(result) == dict:
        stdout = result["stdout"].decode().strip()
        stderr = result["stderr"].decode().strip()
        returncode = result["returncode"]
    else:
        stdout = result.stdout.decode().strip()
        stderr = result.stderr.decode().strip()
        returncode = result.returncode

    if stdout == "":
        stdout = None

    if stderr == "":
        stderr = None

    logging.info("stdout: {}".format(stdout))
    logging.info("stderr: {}".format(stderr))
    logging.info("returncode: {}".format(returncode))
    state.set_state_variable(subsystem, "stdout", stdout)
    state.set_state_variable(subsystem, "stderr", stderr)
    state.set_state_variable(subsystem, "returncode", returncode)

def organize_result(result=None, subprocess_result=None):
    """Construct a dictionary to hold the results of a DCP task."""
    output = {}
    output["result"] = result
    if subprocess_result == None:
        output["calls_program"] = False
        output["stream"] = None
    else:
        if type(subprocess_result) == subprocess.CompletedProcess:
            output["calls_program"] = True
            output["stream"] = {}
            output["stream"]["returncode"] = subprocess_result.returncode
            output["stream"]["stdout"] = subprocess_result.stdout.decode()
            output["stream"]["stderr"] = subprocess_result.stderr.decode()
            output["stream"]["args"] = subprocess_result.args
        else:
            raise DCPServerError                     
    return output

def handle_subprocess_result(camera_name, result, success_message, failure_message, add_details=False):
    store_and_log_subprocess_result(camera_name, result)            
    if result.returncode == 0:
        try:
            details = " Result: {}".format(result.stdout.decode().strip())
        except:
            details = " Result: Details not available."
        if add_details:
            output_message = success_message + details
        else:
            output_message = success_message
    else:
        output_message = failure_message
    dcp_result = organize_result(
        output_message,
        subprocess_result=result
    )
    state.set_state_variable(camera_name,"result",dcp_result)
    
