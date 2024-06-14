import os
import json
#import logging
from filelock import Timeout, FileLock

# Uncomment this if you want to see the file locking debug messages.
# logging.getLogger("filelock").setLevel(logging.DEBUG)

from dragonfly import utility as utility

class StateFileException(Exception):
    "State file is corrupted or does not exist."
    pass

class UnknownDragonflyState(Exception):
    "State is unknown."
    pass

class DragonflyCommandException(Exception):
    "Command does not match definition."
    pass

master_state_file        = "/home/dragonfly/dragonfly-arm/active_optics/state/master_state.json"
lens_state_file          = "/home/dragonfly/dragonfly-arm/active_optics/state/lens_state.json"
fastlens_state_file      = "/home/dragonfly/dragonfly-arm/active_optics/state/fastlens_state.json"
starchaser_state_file    = "/home/dragonfly/dragonfly-arm/active_optics/state/starchaser_state.json"
aluma_state_file         = "/home/dragonfly/dragonfly-arm/active_optics/state/aluma_state.json"
filter_tilter_state_file = "/home/dragonfly/dragonfly-arm/active_optics/state/filter_tilter_state.json"
powerbox_state_file      = "/home/dragonfly/dragonfly-arm/active_optics/state/powerbox_state.json"
apmount_state_file       = "/home/dragonfly/dragonfly-arm/active_optics/state/apmount_state.json"

template_state_file      = "/home/dragonfly/dragonfly-arm/active_optics/state/{}_state.json"

current_master_state = {}
current_lens_state = {}
current_fastlens_state = {}
current_starchaser_state = {}
current_aluma_state = {}
current_filter_tilter_state = {}
current_powerbox_state = {}
current_apmount_state = {}

def state_file_is_accessible(subsystem="master"):
    if (not os.path.exists(template_state_file.format(subsystem)) or (os.stat(master_state_file.format(subsystem)).st_size == 0)):
        return False
    else:
        return True

def create_new_state_file(subsystem="master"):
    default_state = {}
    if subsystem == "master":
        default_state = default_master_state
    elif subsystem == "lens":
        default_state = default_lens_state
    elif subsystem == "fastlens":
        default_state = default_fastlens_state
    elif subsystem == "starchaser":
        default_state = default_starchaser_state
    elif subsystem == "aluma":
        default_state = default_aluma_state
    elif subsystem == "filter_tilter":
        default_state = default_filter_tilter_state
    elif subsystem == "powerbox":
        default_state = default_powerbox_state
    elif subsystem == "apmount":
        default_state = default_apmount_state
    else:
        raise UnknownDragonflyState
    default_state_file = template_state_file.format(subsystem) 
    with open(default_state_file, 'w') as sf:
        json.dump(default_state, sf, indent=4)

def load_state(subsystem="master"):
    global current_master_state
    global current_lens_state
    global current_fastlens_state
    global current_starchaser_state
    global current_aluma_state
    global current_filter_tilter_state
    global current_powerbox_state
    global current_apmount_state

    if subsystem == "master":
        if not state_file_is_accessible(subsystem):
            create_new_state_file(subsystem)
        else:
            state_file = template_state_file.format(subsystem) 
            state_lock_file = state_file.replace('json','lock')
            lock = FileLock(state_lock_file, timeout=3)
            with lock:
                with open(state_file) as sf:
                    current_master_state  = json.load(sf)
    elif subsystem == "lens":
        if not state_file_is_accessible(subsystem):
            create_new_state_file(subsystem)
        else:
            state_file = template_state_file.format(subsystem) 
            state_lock_file = state_file.replace('json','lock')
            lock = FileLock(state_lock_file, timeout=3)
            with lock:
                with open(state_file) as sf:
                    current_lens_state  = json.load(sf)
    elif subsystem == "fastlens":
        if not state_file_is_accessible(subsystem):
            create_new_state_file(subsystem)
        else:
            state_file = template_state_file.format(subsystem) 
            state_lock_file = state_file.replace('json','lock')
            lock = FileLock(state_lock_file, timeout=3)
            with lock:
                with open(state_file) as sf:
                    current_fastlens_state  = json.load(sf)
    elif subsystem == "aluma":
        if not state_file_is_accessible(subsystem):
            create_new_state_file(subsystem)
        else:
            state_file = template_state_file.format(subsystem) 
            state_lock_file = state_file.replace('json','lock')
            lock = FileLock(state_lock_file, timeout=3)
            with lock:
                with open(state_file) as sf:
                    current_aluma_state  = json.load(sf)
    elif subsystem == "starchaser":
        if not state_file_is_accessible(subsystem):
            create_new_state_file(subsystem)
        else:
            state_file = template_state_file.format(subsystem) 
            state_lock_file = state_file.replace('json','lock')
            lock = FileLock(state_lock_file, timeout=3)
            with lock:
                with open(state_file) as sf:
                    current_starchaser_state  = json.load(sf)
    elif subsystem == "filter_tilter":
        if not state_file_is_accessible(subsystem):
            create_new_state_file(subsystem)
        else:
            state_file = template_state_file.format(subsystem) 
            state_lock_file = state_file.replace('json','lock')
            lock = FileLock(state_lock_file, timeout=3)
            with lock:
                with open(state_file) as sf:
                    current_filter_tilter_state  = json.load(sf)
    elif subsystem == "powerbox":
        if not state_file_is_accessible(subsystem):
            create_new_state_file(subsystem)
        else:
            state_file = template_state_file.format(subsystem) 
            state_lock_file = state_file.replace('json','lock')
            lock = FileLock(state_lock_file, timeout=3)
            with lock:
                with open(state_file) as sf:
                    current_powerbox_state  = json.load(sf)
    elif subsystem == "apmount":
        if not state_file_is_accessible(subsystem):
            create_new_state_file(subsystem)
        else:
            state_file = template_state_file.format(subsystem) 
            state_lock_file = state_file.replace('json','lock')
            lock = FileLock(state_lock_file, timeout=3)
            with lock:
                with open(state_file) as sf:
                    current_apmount_state  = json.load(sf)
    else:
        raise UnknownDragonflyState

def save_state(subsystem="master"):
    state = {}
    if subsystem == "master":
        state = current_master_state
    elif subsystem == "lens":
        state = current_lens_state
    elif subsystem == "fastlens":
        state = current_fastlens_state
    elif subsystem == "starchaser":
        state = current_starchaser_state
    elif subsystem == "aluma":
        state = current_aluma_state
    elif subsystem == "filter_tilter":
        state = current_filter_tilter_state
    elif subsystem == "powerbox":
        state = current_powerbox_state
    elif subsystem == "apmount":
        state = current_apmount_state
    else:
        raise UnknownDragonflyState
    state_file = template_state_file.format(subsystem) 
    state_lock_file = state_file.replace('json','lock')
    lock = FileLock(state_lock_file, timeout=3)
    with lock:
        with open(state_file, 'w') as sf:
            json.dump(state, sf, indent=4)


def get_state_variable(subsystem, keyword):
    load_state(subsystem)
    state = {}
    if subsystem == "master":
        state = current_master_state
    elif subsystem == "lens":
        state = current_lens_state
    elif subsystem == "fastlens":
        state = current_fastlens_state
    elif subsystem == "starchaser":
        state = current_starchaser_state
    elif subsystem == "aluma":
        state = current_aluma_state
    elif subsystem == "filter_tilter":
        state = current_filter_tilter_state
    elif subsystem == "powerbox":
        state = current_powerbox_state
    elif subsystem == "apmount":
        state = current_apmount_state
    else:
        raise UnknownDragonflyState
    value = utility.convert_to_number_or_bool_or_None(state[keyword])
    return value

def set_state_variable(subsystem, keyword, value):
    load_state(subsystem)
    state = {}
    if subsystem == "master":
        state = current_master_state
    elif subsystem == "lens":
        state = current_lens_state
    elif subsystem == "fastlens":
        state = current_fastlens_state
    elif subsystem == "starchaser":
        state = current_starchaser_state
    elif subsystem == "aluma":
        state = current_aluma_state
    elif subsystem == "filter_tilter":
        state = current_filter_tilter_state
    elif subsystem == "powerbox":
        state = current_powerbox_state
    elif subsystem == "apmount":
        state = current_apmount_state
    else:
        raise UnknownDragonflyState
    state[keyword] = utility.convert_to_number_or_bool_or_None(value)
    save_state(subsystem)

    
def clear_output_streams(subsystem):
    """Clears the stdin and stdout keywords in a state file.

    Args:
        subsystem (string): dragonfly subsysytem ("aluma", "powerbox", etc.)

    Raises:
        UnknownDragonflyState: the requested subsystem is unknown.
    """
    load_state(subsystem)
    state = {}
    if subsystem == "master":
        state = current_master_state
    elif subsystem == "lens":
        state = current_lens_state
    elif subsystem == "fastlens":
        state = current_fastlens_state
    elif subsystem == "starchaser":
        state = current_starchaser_state
    elif subsystem == "aluma":
        state = current_aluma_state
    elif subsystem == "filter_tilter":
        state = current_filter_tilter_state
    elif subsystem == "powerbox":
        state = current_powerbox_state
    elif subsystem == "apmount":
        state = current_apmount_state
    else:
        raise UnknownDragonflyState
    state["stdout"] = None
    state["stderr"] = None
    state["result"] = None
    state["stream"] = None
    state["calls_program"] = None
    save_state(subsystem)    

# Define the default state.
default_master_state = {}
default_lens_state = {}
default_fastlens_state = {}
default_aluma_state = {}
default_starchaser_state = {}
default_filter_tilter_state = {}
default_powerbox_state = {}
default_apmount_state = {}

default_lens_state = {
    "owner": None,
    "verb": None,
    "noun": None,
    "arg1": None,
    "arg2": None,
    "arg3": None,
    "result": None,
    "stdout": None,
    "stderr": None,
    "returncode": None,
    "x": 0,
    "y": 0,
    "z": 0,
    "z_max": 0,
    "initialized": False,
    "present": False,
    "locked": True,
    "focus_date": None,
    "focus_temperature": None,
    "busy": False,
    "current_action": "idle",
    "error_status": 0,
    "selected": False
}

default_fastlens_state = {
    "owner": None,
    "verb": None,
    "noun": None,
    "arg1": None,
    "arg2": None,
    "arg3": None,
    "result": None,
    "stdout": None,
    "stderr": None,
    "returncode": None,
    "x": 0,
    "y": 0,
    "z": 0,
    "z_max": 0,
    "initialized": False,
    "present": False,
    "locked": True,
    "focus_date": None,
    "focus_temperature": None,
    "busy": False,
    "current_action": "idle",
    "error_status": 0,
    "selected": False
}

default_starchaser_state = {
    "owner": None,
    "verb": None,
    "noun": None,
    "arg1": None,
    "arg2": None,
    "arg3": None,
    "result": None,
    "stdout": None,
    "stderr": None,
    "returncode": None,
    "started": None,
    "finished":  None,
    "present": False,
    "camera_number": 0,
    "imtype": "light",
    "savedir": "/tmp",
    "next_filename": None,
    "last_filename": None,
    "graphics_filename": "/tmp/guider.png",
    "graphics_type": 0,
    "exptime": 10,
    "binning": 2,
    "include_overscan": False,
    "fwhm": 0,
    "rms": 0,
    "iteration": 0,
    "log": "/tmp/guider_log.txt",
    "exposing": False,
    "calculating": False,
    "guiding": False,
    "busy": False,
    "current_action": "idle",
    "repeat": False,
    "keep": True,
    "error_status": 0,
    "selected": False
}

default_aluma_state = {
    "owner": None,
    "verb": None,
    "noun": None,
    "arg1": None,
    "arg2": None,
    "arg3": None,
    "result": None,
    "stdout": None,
    "stderr": None,
    "returncode": None,
    "started": None,
    "finished":  None,
    "present": False,
    "camera_number": 1,
    "imtype": "light",
    "savedir": "/tmp",
    "next_filename": None,
    "last_filename": None,
    "graphics_filename": "/tmp/tmp.png",
    "graphics_type": 0,
    "exptime": 0,
    "binning": 1,
    "include_overscan": False,
    "fwhm": 0,
    "dirname": None,
    "setpoint": None,
    "temperature": None,
    "power": None,
    "heatsink": None,
    "exposing": False,
    "calculating": False,
    "busy": False,
    "current_action": "idle",
    "error_status": 0,
    "repeat": False,
    "keep": True,
    "selected": False
}

default_filter_tilter_state = {
    "owner": None,
    "verb": None,
    "noun": None,
    "arg1": None,
    "arg2": None,
    "arg3": None,
    "result": None,
    "stdout": None,
    "stderr": None,
    "started": None,
    "finished":  None,
    "present": False,
    "angle": 0,
    "central_wavelength": 0,
    "calibration_date": 0,
    "calibration_altitude": 0,
    "calibration_azimuth": 0,
    "busy": False,
    "current_action": "idle",
    "error_status": 0,
    "selected": False
}

default_powerbox_state = {
    "owner": None,
    "verb": None,
    "noun": None,
    "arg1": None,
    "arg2": None,
    "arg3": None,
    "result": None,
    "stdout": None,
    "stderr": None,
    "present": False,
    "P1": False,
    "temperature": 0,
    "humidity": 0,
    "current": None,
    "busy": False,
    "current_action": "idle",
    "error_status": 0,
    "selected": False
}

default_apmount_state = {
    "owner": None,
    "verb": None,
    "noun": None,
    "arg1": None,
    "arg2": None,
    "arg3": None,
    "result": None,
    "stdout": None,
    "stderr": None,
    "present": False,
    "ra": False,
    "dec": False,
    "epoch": 2000,
    "ra": None,
    "dec": None,
    "alt": None,
    "pier_side": None,
    "latitude": None,
    "longitude": None,
    "timezone": None,
    "is_connected": False,
    "is_slewing": False,
    "busy": False,
    "current_action": "idle",
    "error_status": 0,
    "selected": False
}

default_master_state = {
    "lens": default_lens_state,
    "fastlens": default_fastlens_state,
    "aluma": default_aluma_state,
    "starchaser": default_starchaser_state,
    "filter_tilter": default_filter_tilter_state,
    "powerbox": default_powerbox_state,
    "apmount": default_apmount_state
}
 
# Make sure we load the current state when we load the module.
load_state("master")
load_state("lens")
load_state("fastlens")
load_state("aluma")
load_state("starchaser")
load_state("filter_tilter")
load_state("powerbox")
load_state("apmount")