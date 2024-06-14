import os
import logging
import subprocess

from dragonfly import utility as utility

log = logging.getLogger('team_dragonfly')
log.addHandler(logging.NullHandler())

# If you want to see information messages in iPython interactive sessions:
# import logging
# log = logging.getLogger('team_dragonfly')
# log.setLevel(logging.INFO)

class ImageFileException(Exception):
    "Thrown when an anomaly exists in an image file."
    pass

def check_image_file(filename):
    "Determine if a file is a Dragonfly FITS image."
    if not os.path.isfile(filename):
        raise ImageFileException
    if not filename.lower().endswith(('.fits','.fit')):
        raise ImageFileException
    if (not "SCP31300M" in filename) and (not "AL694M" in filename):
        raise ImageFileException

def expose(camera, exptime, imtype, output_filename=None, savedir=None, include_overscan=False):
    """
    Take an exposure on a camera.

    Example 1:

        from dragonfly import camera
        from dragonfly import graphics

        camera.expose(1, 0.1, "light", "/tmp/foobar.fits")
        graphics.create_png("/tmp/foobar.fits", "/tmp/foobar.png", 2, 5, "sqrt", False)
        !./imgcat.sh /tmp/foobar.png
    """
    exptime = utility.convert_to_number_or_bool_or_None(exptime)  
    include_overscan = utility.convert_to_number_or_bool_or_None(include_overscan)    
    
    max_readout_time = 7
    safe_expose_cmd = "/home/dragonfly/dragonfly-arm/active_optics/dcp/final_expose.py"

    camera_string = str(int(camera))
    exptime_string = str(exptime)
    log.info("Exposing camera {} for {}s".format(camera_string, exptime_string))

    command = [ "sudo",
                "/usr/bin/python3",
                safe_expose_cmd,
                "--camera", camera_string,
                "--duration", exptime_string ]
    
    # Add an optional filename. If the filename is None or is "auto", then let
    # the dfcore program automatically pick a filename.
    try:
        if output_filename != None:
            file_info = os.path.split(output_filename)
            dirname = file_info[0]
            filename = file_info[1]
            if filename.lower() != "auto":
                command.append("--filename")
                command.append(filename)
    except:
        pass
        
    # Add an optional save directory
    try:
        # If an explicit path is given as part of the filename argument, this
        # overrides everything.
        if dirname != '':
            command.append("--savedir")
            command.append(dirname)
        elif savedir != None:
            command.append("--savedir")
            command.append(savedir)           
    except:
        pass
    
    # Add an optional image type. The default is 'light', but None is also permitted, so
    # we rely on the exception handling system to preserve appropriate defaults.
    try:
        if imtype.lower() == "dark":
            command.append("--dark")
        if imtype.lower() == "bias":
            command.append("--bias")
        if imtype.lower() == "flat":
            command.append("--flat")
    except:
        pass  
        
    # We should return a process_data dictionary no matter what. Since Dostoyevsky
    # was right, there are may ways things can go wrong, and only one way things can
    # go right. So we will make the default that an error has occurred allow the
    # the subprocess calling routine to override this.
    process_data = {}
    process_data["stdout"] = ""
    process_data["stderr"] = "Error. Camera command filed"
    process_data["returncode"] = 1
    
    if not include_overscan:
        command.append("--disable_overscan")
     
    try:
        log.info("Executing: {}".format(" ".join(command)))
        process_data = subprocess.run(command, timeout = exptime + max_readout_time, 
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if process_data.returncode == 0:
            log.info("Exposure completed successfully.")            
        else:
            log.info("Error. Exposure failed." )
        return process_data
    except subprocess.TimeoutExpired:
        print('Error. Timed out. Exposure failed.')
        process_data = {}
        process_data["stdout"] = b""
        process_data["stderr"] = b"Error. Camera command timed out."
        process_data["returncode"] = 1
        log.info("Error. Exposure timed out." )
        return process_data

def find_camera_number(subsystem):
    """
    List connected camera system.
    """
    log.info("Listing available cameras.")
    command = ["sudo", "/home/dragonfly/dragonfly-arm/core/dfcore", "list"]
    try:
        log.info("Executing: {}".format(" ".join(command)))
        process_data = subprocess.run(command, timeout = 5, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if process_data.returncode == 0:
            stdout = process_data.stdout.decode().lower()
            try:
                camnum = [m for m in stdout.split("\n") if subsystem.lower() in m][0].split(' --- ')[0].split(' ')[1]
                log.info("{} corresponds to camera number {}".format(subsystem,camnum))
                return int(camnum)
            except IndexError:
                log.info("{} not found".format(subsystem))
                return -1 
        else:
            process_data = {}
            process_data["stdout"] = b""
            process_data["stderr"] = b"Error. Sub-process to find cameras reported an error. (Is power on? Is camera plugged in?)."
            process_data["returncode"] = 1
            log.info("Error. Sub-process to find cameras reported an error. (Is power on? Is camera plugged in?).")
            return -1
    except subprocess.TimeoutExpired:
        print('Error. Could not find camera.')
        process_data = {}
        process_data["stdout"] = b""
        process_data["stderr"] = b"Error. Could not run process to find camera."
        process_data["returncode"] = 1
        log.info("Error. Could not find camera." )

def list():
    """
    List connected camera system.
    """
    log.info("Listing available cameras.")
    command = ["sudo", "/home/dragonfly/dragonfly-arm/core/dfcore", "list"]
    try:
        log.info("Executing: {}".format(" ".join(command)))
        process_data = subprocess.run(command, timeout = 5, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return process_data
    except subprocess.TimeoutExpired:
        print('Error. Timed out. Camera communication failed.')
        
def get_temperature():
    """
    Check check the temperature of the CCD.
    """
    log.info("Checking camera temperature.")
    command = ["sudo", "/home/dragonfly/dragonfly-arm/core/dfcore", "cool", "get"]
    try:
        log.info("Executing: {}".format(" ".join(command)))
        process_data = subprocess.run(command, timeout = 5, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return process_data
    except subprocess.TimeoutExpired:
        print('Error. Timed out. Camera communication failed.')
        
def enable(setpoint):
    """
    Enable CCD cooling.
    """
    log.info("Enabling CCD cooling.")
    command = ["sudo", "/home/dragonfly/dragonfly-arm/core/dfcore", "cool", "set", setpoint]
    try:
        log.info("Executing: {}".format(" ".join(command)))
        process_data = subprocess.run(command, timeout = 5, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(process_data)
        return process_data
    except subprocess.TimeoutExpired:
        print('Error. Timed out. Camera communication failed.')
        
def disable():
    """
    Enable CCD cooling.
    """
    log.info("Disabling CCD cooling.")
    command = ["sudo", "/home/dragonfly/dragonfly-arm/core/dfcore", "cool", "disable"]
    try:
        log.info("Executing: {}".format(" ".join(command)))
        process_data = subprocess.run(command, timeout = 5, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return process_data
    except subprocess.TimeoutExpired:
        print('Error. Timed out. Camera communication failed.')
