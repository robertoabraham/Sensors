import sys
import re
import subprocess
import logging

from dragonfly import utility as utility
from dragonfly import state as state

log = logging.getLogger('team_dragonfly')
log.addHandler(logging.NullHandler())

# If you want to see information messages in iPython interactive sessions:
# import logging
# log = logging.getLogger('team_dragonfly')
# log.setLevel(logging.INFO)

if (sys.version_info[0] != 3):
    raise Exception("Sorry - I only work under python3")

class CanonLensError(Exception):
    "Thrown when an error occurs in trying to communicate with a Canon lens."
    pass

class CanonLensISError(Exception):
    "Thrown when an error occurs in trying to send an IS command to a Canon lens."
    pass

class CanonLensCalibrationError(Exception):
    "Thrown when an error occurs in trying to calibrate a Canon lens."
    pass

def set_focus_position(focus_value):
    "Sets the current focuser position to a specified digital setpoint."
    log.info("Setting focus position to: {}".format(focus_value))
    focus_command = "fa" + str(int(focus_value))
    result = run_command(focus_command)
    return result

def set_is_x_position(value):
    "Sets the current IS x-axis position to a specified digital setpoint."
    log.info("Setting IS x-axis position to: {}".format(value))
    command = "ix" + str(int(value))
    result = run_command(command)
    return result

def set_is_y_position(value):
    "Sets the current IS y-axis position to a specified digital setpoint."
    log.info("Setting IS y-axis position to: {}".format(value))
    command = "iy" + str(int(value))
    result = run_command(command)
    return result

def move_focus_position(delta_focus_value):
    "Displaces the current focus position by a specified number of digital units."
    log.info("Moving focus position by: {}".format(delta_focus_value))
    focus_command = "mf" + str(int(delta_focus_value))
    result = run_command(focus_command)
    return result

def get_focus_position():
    "Gets the current focus position on a Canon lens."
    focus_command = "pf"
    log.info("Getting focus position.")
    data = run_command(focus_command)
    focus_position = 0
    try:
        # The run_command returns an object whose stdout is a byte string with
        # lines separated by '\n'. The relevant line starts looks something like:
        # 'Result: Focus position: XXXXX' where XXXXX is the number we want.

        result_line = utility.find_line_in_subprocess_stdout(data, 'Result')
        focus_position = int(result_line.split()[-1])
        log.info("Current focus position: {}".format(focus_position))
    except:
        log.error("Could not get focus position.")
        raise CanonLensError
    return focus_position

def get_is_position():
    "Gets the current focus position on a Canon lens."
    focus_command = "pi"
    log.info("Getting IS X-Y position.")
    data = run_command(focus_command)
    try:
        result_line = data.stdout.decode()
        x_position = int(result_line.split()[-5])
        y_position = int(result_line.split()[-1])
        log.info("Current IS X,Y position: {},{}".format(x_position, y_position))
        return [x_position, y_position]
    except:
        raise CanonLensError

def check_lens_presence():
    "Returns a Bool indicating whether or not a lens is connected."
    command = "lp"
    log.info("Checking for lens presence.")
    result = run_command(command)
    return result

def activate_image_stabilization():
    "Activates the image stabilization system. Result returned as a Bool."
    command = "is1"
    log.info("Activating image stabilization.")
    result = run_command(command)
    return result

def deactivate_image_stabilization():
    "Deativates the image stabilization system. Result returned as a Bool."
    command = "is0"
    log.info("Deactivating image stabilization.")
    result = run_command(command)
    return result

def open_aperture():
    "Fully opens lens aperture."
    command = "in"
    log.info("Opening lens aperture.")
    data = run_command(command)
    return data

def move_focus_to_infinity():
    "Focuses lens to infinity."
    command = "mi"
    log.info("Moving lens to infinity focus.")
    data = run_command(command)
    return data

def move_focus_to_closest_focus_position():
    "Focuses lens to closest focus position."
    command = "mz"
    log.info("Moving lens to closest focus position.")
    data = run_command(command)
    return data

def learn_focus_range():
    "Calibrates lens focus range (minimum and maximum setpoints)"
    command = "la"
    log.info("Calibrating lens focus range")
    data = run_command(command)
    return data

def set_zeropoint():
    "Sets the minimum position of the lens to be zero"
    command = "sf0"
    log.info("Setting lens zeropoint")
    data = run_command(command)
    return data

def initialize():
    "Initializes a lens for first use."
    try:
        results = {}
        
        # Exercise full range
        data = learn_focus_range()
        if data.returncode != 0:
            raise CanonLensCalibrationError
        else:
            results['learn'] = data
    
        # Move to nearest focus
        data = move_focus_to_closest_focus_position()
        if data.returncode != 0:
            raise CanonLensCalibrationError
        else:
            results['move_near'] = data
            
        # Set lens so 0 ADU is the nearest focus position
        data = set_zeropoint()
        if data.returncode != 0:
            raise CanonLensCalibrationError
        else:
            results['zeropoint'] = data
        
        # Move to farthest focus position
        data = move_focus_to_infinity()
        if data.returncode != 0:
            raise CanonLensCalibrationError
        else:
            results['move_far'] = data      
            
        # Store the farthest focus position as a state variable. 
        logging.info("Recording z_max state variable")  
        pos = get_focus_position()
        state.set_state_variable('lens', 'z', pos)      
        state.set_state_variable('lens', 'z_max', pos)
        
        # Leave the focus roughly near the midpoint.
        logging.info("Moving focus to approximate midpoint")
        data = set_focus_position(10000)
        results['move_middle'] = data 
        if data.returncode != 0:
            raise CanonLensCalibrationError
        else:
            pos = get_focus_position()
            state.set_state_variable('lens', 'z', pos)
        return results
    except:
        raise CanonLensCalibrationError
    

def run_command(command, verbose=False, prefix=""):
    "Runs a low-level Canon lens command. Result is returned in a Python subprocess object."
    if command is not None:
        command_line = "/usr/bin/python3 /home/dragonfly/dragonfly-arm/active_optics/dcp/drivers/lens_controller.py -c"
        command_list = command_line.split()
        command_list.append(command)
        if verbose:
            print(prefix + "Running: {}".format(command_line + " '" + command +"'"))
        result = subprocess.run(command_list, capture_output=True, check=True)
        return result
