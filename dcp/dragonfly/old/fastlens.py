import sys
import time
import logging

from dragonfly import utility as utility
from dragonfly import state as state

subsystem_name = 'fastlens'

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

def check_lens_presence(arduino, verbose=False):
    "Returns a Bool indicating whether or not a lens is connected."
    command = "lp"
    log.info("Checking for lens presence.")
    lines = run_command(arduino, command, verbose)
    # The last line returned by the Arduino is always "Received: Done." so the line 
    # with the useful information is always the second to the last line.
    result = lines[-2]
    return result

def get_focus_position(arduino, verbose=False):
    "Gets the current focus position on a Canon lens."
    focus_command = "pf"
    log.info("Getting focus position.")
    result = run_command(arduino, focus_command, verbose)
    focus_position = 0
    try:
        # The run_command returns a list containing the communication to and
        # from the Arduino. The relevant line looks like:
        # 'Focus position: XXXXX' where XXXXX is the number we want.
        result_line = [line for line in result if 'Focus position:' in line][0]
        focus_position = int(result_line.split()[-1])
        log.info("Current focus position: {}".format(focus_position))
    except:
        log.error("Could not get focus position.")
        raise CanonLensError
    return focus_position

def set_focus_position(arduino, focus_value, verbose=False):
    "Sets the current focuser position to a specified digital setpoint."
    log.info("Setting focus position to: {}".format(focus_value))
    command = "fa" + str(int(focus_value))
    lines = run_command(arduino, command, verbose)
    result = lines[-2]
    return result

def set_is_x_position(arduino, value, verbose=False):
    "Sets the current IS x-axis position to a specified digital setpoint."
    log.info("Setting IS x-axis position to: {}".format(value))
    command = "ix" + str(int(value))
    lines = run_command(arduino, command, verbose)
    result = lines[-2]
    return result

def set_is_y_position(arduino, value, verbose=False):
    "Sets the current IS y-axis position to a specified digital setpoint."
    log.info("Setting IS y-axis position to: {}".format(value))
    command = "iy" + str(int(value))
    lines = run_command(arduino, command, verbose)
    result = lines[-2]
    return result

def get_is_position(arduino, verbose=False):
    "Gets the current focus position on a Canon lens. Returns a list."
    command = "pi"
    log.info("Getting IS X-Y position.")
    lines = run_command(arduino, command, verbose)
    result_line = lines[-2]
    try:
        x_position = int(result_line.split()[-5])
        y_position = int(result_line.split()[-1])
        log.info("Current IS X,Y position: {},{}".format(x_position, y_position))
        return [x_position, y_position]
    except:
        raise CanonLensError

def activate_image_stabilization(arduino, verbose=False):
    "Activates the image stabilization system."
    command = "is1"
    log.info("Activating image stabilization.")
    lines = run_command(arduino, command, verbose)
    result = lines[-2]
    return result

def deactivate_image_stabilization(arduino, verbose=False):
    "Activates the image stabilization system."
    command = "is0"
    log.info("Deactivating image stabilization.")
    lines = run_command(arduino, command, verbose)
    result = lines[-2]
    return result

def open_aperture(arduino, verbose=False):
    "Fully opens lens aperture."
    command = "in"
    log.info("Opening lens aperture.")
    lines = run_command(arduino, command, verbose)
    result = lines[-2]
    return result

def move_focus_to_infinity(arduino, verbose=False):
    "Focuses lens to infinity."
    command = "mi"
    log.info("Moving lens to infinity focus.")
    lines = run_command(arduino, command, verbose)
    result = lines[-2]
    return result

def move_focus_to_closest_focus_position(arduino, verbose=False):
    "Focuses lens to closest focus position."
    command = "mz"
    log.info("Moving lens to closest focus position.")
    lines = run_command(arduino, command, verbose)
    result = lines[-2]
    return result

def learn_focus_range(arduino, verbose=False):
    "Calibrates lens focus range (minimum and maximum setpoints)"
    command = "la"
    log.info("Calibrating lens focus range")
    lines = run_command(arduino, command, verbose)
    result = lines[-2]
    return result

def set_zeropoint(arduino, verbose=False):
    "Sets the minimum position of the lens to be zero"
    command = "sf0"
    log.info("Setting lens zeropoint")
    lines = run_command(arduino, command, verbose)
    result = lines[-2]
    return result

def initialize(arduino, verbose=False):
    "Initializes a lens for first use."
    try:
        results = {}
        
        # Exercise full range
        data = learn_focus_range(arduino, verbose)
        results['learn'] = data
    
        # Move to nearest focus
        data = move_focus_to_closest_focus_position(arduino, verbose)
        results['move_near'] = data
            
        # Set lens so 0 ADU is the nearest focus position
        data = set_zeropoint(arduino, verbose)
        results['zeropoint'] = data
        
        # Move to farthest focus position
        data = move_focus_to_infinity(arduino, verbose)
        results['move_far'] = data      
            
        # Store the farthest focus position as a state variable. 
        logging.info("Recording z_max state variable")  
        pos = int(get_focus_position(arduino, verbose))
        state.set_state_variable(subsystem_name, 'z', pos)      
        state.set_state_variable(subsystem_name, 'z_max', pos)
        
        # Leave the focus roughly near the midpoint.
        logging.info("Moving focus to approximate midpoint")
        data = set_focus_position(arduino, 10000, verbose)
        results['move_middle'] = data 
        pos = int(get_focus_position(arduino, verbose))
        state.set_state_variable(subsystem_name, 'z', pos)
        return results
    except:
        raise CanonLensCalibrationError

# Send a command to the Arduino. The result is an array containing strings
# returned by the Arduino.
def run_command(arduino, command, verbose=False, super_verbose=False):
    "Runs a low-level lens command through the Arduino."
    if command is not None:
        command = command + '\n'
        command = command.lower()
        arduino.flush()
        arduino.write(command.encode())
        line = ""
        lines = []
        logging.info("Sending command: {}".format(command.rstrip()))
        while(True):
            if arduino.inWaiting()>0:
                time.sleep(0.01)
                c = arduino.read().decode()
                if c == '\n':
                    lines.append(line.lstrip().rstrip())
                    if super_verbose:
                        print("  Received: {}".format(line.lstrip().rstrip()))
                    if "Done" in line:
                        break
                    line = ""
                line = line + c
        #result = lines[-2].lstrip().rstrip()
        #logging.info("Result: {}\n".format(result))
        arduino.flush()
        if verbose:
            logging.info("Result: {}\n".format(lines))
        #return result
        return(lines)
