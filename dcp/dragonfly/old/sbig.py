import os
import time
import logging
import subprocess
import logging
import threading
import signal
import sys

from dragonfly import utility as utility
from dragonfly.log import DFLog

log = logging.getLogger('team_dragonfly')
log.addHandler(logging.NullHandler())


class DLAPICameraError(Exception):
    """Exception raised when a camera error occurs."

    Attributes:
        msg - error message
    """
    
    def __init__(self, message:str = "Camera error."):
        self. message = message
        super().__init__(self.message)
    pass


class DLAPIImageFileError(Exception):
    "Thrown when an anomaly exists in an image file."
    pass


class DLAPICamera(object):
    """A Diffraction Limited (SBIG) camera.  
    """

    def __init__(self, model:str="aluma", dirname:str="/tmp", verbose:bool=False):
        """Initializes the camera object.

        Args:
            model (string): name of the camera model (e.g. "aluma" or "starchaser"). Defaults to "aluma".
            verbose (bool, optional): sets verbose mode on (True) or off (False). Defaults to False.
        """
        self.model = model
        self.dirname = dirname
        self.verbose = verbose
        
        self._state = {}     
        self._state['CameraNumber'] = None
        self._state['CameraModel'] = model
        self._state['SetpointTemperature'] = None
        self._state['Binning'] = None
        self._state['IncludeOverscan'] = None
        self._state['PowerDrawPercent'] = None
        self._state['SensorTemperatureC'] = None
        self._state['HeatsinkTemperatureC'] = None
        self._state['Binning'] = 1
        self._state['IncludeOverscan'] = None
        self._state['Activity'] = None
        self._state['IsConnected'] = False
        self._state['IsExposing'] = False
        self._state['IsCooling'] = False
        
        self.logger = DFLog(f'SBIGCamera({model})').logger
        
        self.command_running = False
        
        self._exposure_process = None
        self._last_image = None
        
        self._exposure_result = {}
        self._exposure_result["stdout"] = None
        self._exposure_result["stderr"] = None
        self._exposure_result["returncode"] = None
        
        self._exposure_time = None
        self._exposure_start_time = None
        
        self._image_stack = []


    @property
    def state(self):
        return self._state
    
    
    @property
    def exposure_start_time(self):
        return time.ctime(self._exposure_start_time)
    
    
    @property
    def last_image(self):
        return self._last_image
    

    @property
    def image_stack(self):
        return self._image_stack


    @property
    def exposure_result(self):
        return self._exposure_result


    def connect(self):
        """Connects to the camera.
        """
        log.info("Connecting to camera.")
        self.state['CameraNumber'] = self._find_camera_number(self.model)
        if self.state['CameraNumber'] == -1:
            raise DLAPICameraError("Error. Could not connect to camera.")
        else:
            if self.model == "aluma":
                self.state['IncludeOverscan'] = True
            else:
                self.state['IncludeOverscan'] = False
            self._refresh_status()
            self.state['IsConnected'] = True
            return(f"Camera {self.state['CameraNumber']} connected.")


    def set_temperature(self, temperature:float):
        """Sets the camera temperature setpoint. (Does not automatically start cooling).

        Args:
            temperature (float): Temperature in degrees Celsius.
        """
        self.state['SetpointTemperature'] = temperature

        
    def set_binning(self, binning:int):
        """Sets the camera binning.

        Args:
            binning (int): Binning factor (e.g. 2 is 2x2 binning).
        """
        self.state['Binning'] = binning
        
        
    def set_directory(self, dirname:str):
        """Sets the save directory.

        Args:
            dirname (string): Directory to save images in.
        """
        self.dirname = dirname
        
        
    def set_verbose(self, verbose:bool):
        """Sets whether or not to print verbose output.

        Args:
            verbose (bool): True or False.
        """
        self.verbose = verbose
        

    def get_status(self):
        """Report camera status.

        Returns:
            dict: Dictionary with keys "CameraModel", "CameraNumber", "SetpointTemperature", 
               "Binning", "IncludeOverscan", "PowerDrawPercent", "SensorTemperatureC", 
               "HeatsinkTemperatureC", "IsConnected", "IsExposing", "IsCooling"
        """
        self._refresh_status()
        return self.state      
            
        
    def expose(self, exptime, imtype, output_filename=None, wait=True):
        """Takes an exposure on a DLAPI camera.

        Args:
            exptime (float): integration time
            imtype (strong): "light", "dark", "bias", or "flat"
            output_filename (string, optional): output filename. Defaults to None, which means that the dfcore
                program will automatically pick a filename.
            wait (bool, optional): wait for image taking to complete before returning. Defaults to True.

        Returns:
            string: "Exposure started."
        """
        command = self._dfcore_command_line(exptime, imtype, output_filename)
        log.info("Executing: {}".format(" ".join(command)))
        try:
            self.state['IsExposing'] = True
            self._exposure_time = exptime
            self._exposure_start_time = time.time()
            self._exposure_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except:
            self.exposure_start_time = None
            self.state['IsExposing'] = False
        
        if wait:
            while self.state['IsExposing']:
                time.sleep(0.1)
                result = self.check_exposure()
            return result
        else:
            return "Exposure started."


    def check_exposure(self):
        """Checks if an exposure is complete and, if so, reads it out and saves it to disk.

        Raises:
            DLAPICameraError: Error that occurs when the exposure times out.

        Returns:
            string: One of: "No exposure in progress", "Exposure in progress." or "Exposure completed."
        """
        max_readout_time = 15
        if self._exposure_process is None:
            self._state["Activity"] = "Idle."
            return "No exposure in progress."
        if ((self._exposure_process.poll() is None) and 
            (time.time() - self._exposure_start_time) > (self._exposure_time + max_readout_time)):
            # Things are taking too long. Kill the exposure
            self.state['IsExposing'] = False
            self._exposure_process.kill()
            self._exposure_process = None
            self._exposure_result["stdout"] = ""
            self._exposure_result["stderr"] = "Exposure timed out."
            self._exposure_result["returncode"] = 1
            self._state["Activity"] = "Idle."
            raise DLAPICameraError("Error. Exposure timed out.")
        if self._exposure_process.poll() is None:
            self._state["Activity"] = "Exposing."
            return "Exposure in progress."
        else:
            # Exposure is complete
            self.state['IsExposing'] = False
            stdout, stderr = self._exposure_process.communicate()
            self._exposure_result["stdout"] = stdout.decode().rstrip()
            self._exposure_result["stderr"] = stderr.decode().rstrip()
            self._exposure_result["returncode"] = self._exposure_process.returncode
            image_name =  stdout.decode().rstrip()
            self._image_stack.append(image_name)
            self._last_image = image_name
            self._exposure_process = None
            self._state["Activity"] = "Idle." 
            return "Exposure completed."
        

    def eta(self):
        """Returns the estimated time until the current exposure is complete.

        Returns:
            float: time in seconds until exposure is complete.
        """
        if self._exposure_process is None:
            return 0.0
        else:
            return round(self._exposure_time - (time.time() - self._exposure_start_time),2)


    def start_cooling(self, setpoint=None):
        """Starts cooling the camera.

        Args:
            setpoint (float, optional): temperature to cool down to. If not set, take from status dictionary.

        Raises:
            DLAPICameraError: Error that occurs when the camera cannot be cooled to the desired temperature.

        Returns:
            CompletedProcess object: completed subprocess information.
        """
        log.info("Enabling CCD cooling.")
        
        if setpoint is not None:
            self.state['SetpointTemperature'] = setpoint
        
        command = ["sudo", "/home/dragonfly/dragonfly-arm/core/dfcore", "cool", "set", 
                   str(self.state['SetpointTemperature'])]
        try:
            log.info("Executing: {}".format(" ".join(command)))
            process_data = subprocess.run(command, timeout = 5, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if process_data.returncode == 0:
                self.state['IsCooling'] = True
                return "Camera cooling enabled."
            else:
                raise DLAPICameraError("Error. Camera cooling failed.")
        except subprocess.TimeoutExpired:
            raise DLAPICameraError("Error. Timed out. Camera communication failed.")


    def stop_cooling(self):
        """Disables cooling.

        Raises:
            DLAPICameraError: Error raised if the camera cooling cannot be disabled.

        Returns:
            CompletedProcess object: completed subprocess information.
        """
        log.info("Disabling CCD cooling.")
        command = ["sudo", "/home/dragonfly/dragonfly-arm/core/dfcore", "cool", "disable"]
        try:
            log.info("Executing: {}".format(" ".join(command)))
            process_data = subprocess.run(command, timeout = 5, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if process_data.returncode == 0:
                self.state['IsCooling'] = False
                return "Camera cooling disabled."
            else:
                raise DLAPICameraError("Error. Camera cooling disabling failed.")
        except subprocess.TimeoutExpired:
            raise DLAPICameraError("Error. Timed out. Camera communication failed.")

        
    # Helper functions below here.

        
    def _check_image_file(self, filename):
        """Determine if a file is a Dragonfly FITS image.

        Args:
            filename (string): pat to FITS file

        Raises:
            DLAPIImageFileError: error raised if the file is not a Dragonfly FITS image.
        """
        if not os.path.isfile(filename):
            raise DLAPIImageFileError
        if not filename.lower().endswith(('.fits','.fit')):
            raise DLAPIImageFileError
        if (not "SCP31300M" in filename) and (not "AL694M" in filename):
            raise DLAPIImageFileError
        
    
    def _list(self):
        """
        List all connected camera systems.
        """
        log.info("Listing available cameras.")
        command = ["sudo", "/home/dragonfly/dragonfly-arm/core/dfcore", "list"]
        try:
            log.info("Executing: {}".format(" ".join(command)))
            process_data = subprocess.run(command, timeout = 5, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return process_data
        except subprocess.TimeoutExpired:
            raise DLAPICameraError("Error. Timed out. Camera communication failed.")
        
        
    def _refresh_status(self):
        """Gets camera temperature information.

        Raises:
            DLAPICameraError: Error that occurs when the camera temperature cannot be read.

        Returns:
            CompletedProcess object: completed subprocess information.
        """
        log.info("Checking camera status.")
        self.check_exposure()
        if self.state['CameraModel'] == "aluma":
            if self.state['IsExposing'] is False:
                command = ["sudo", "/home/dragonfly/dragonfly-arm/core/dfcore", "cool", "get"]
                log.info("Executing: {}".format(" ".join(command)))
                try:
                        result = subprocess.run(command, timeout = 5, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        result_list = result.stdout.decode().split('\n')
                        self.state['PowerDrawPercent'] = float(result_list[0].split(':')[1].replace("%",""))
                        self.state['SensorTemperatureC'] = float(result_list[1].split(':')[1].replace("C",""))
                        self.state['HeatsinkTemperatureC'] = float(result_list[2].split(':')[1].replace("C",""))
                except subprocess.TimeoutExpired:
                    raise DLAPICameraError("Error. Timed out. Camera communication failed.")
        else:
            self.state['PowerDrawPercent'] = None
            self.state['SensorTemperatureC'] = None
            self.state['HeatsinkTemperatureC'] = None
        self.logger.info(self.state)


    def _find_camera_number(self, subsystem):
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
            return -1


    def _dfcore_command_line(self, exptime:float, imtype:str, output_filename:str=None):
        """Creates a list that can be used to execute a dfcore command.

        Args:
            exptime (float): integration time
            imtype (strong): "light", "dark", "bias", or "flat"
            output_filename (string, optional): output filename. Defaults to None, which means that the dfcore
                program will automatically pick a filename.

        Returns:
            _type_: _description_
        """ 
        include_overscan = self.state['IncludeOverscan']
        
        safe_expose_cmd = "/home/dragonfly/dragonfly-arm/active_optics/dcp/final_expose.py"

        camera_string = str(int(self.state['CameraNumber']))
        binning_string = str(self.state["Binning"])
        exptime_string = str(exptime)
        log.info("Exposing camera {} for {}s".format(camera_string, exptime_string))

        command = [ "sudo",
                    "/usr/bin/python3",
                    safe_expose_cmd,
                    "--camera", camera_string,
                    "--binx", binning_string,
                    "--biny", binning_string,
                    "--duration", exptime_string ]
        
        # Add an optional filename. If the filename is None or is "auto", then let
        # the dfcore program automatically pick a filename.
        dirname = ''
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
            else:
                command.append("--savedir")
                command.append(self.dirname)           
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
        
        if not include_overscan:
            command.append("--disable_overscan")
            
        return(command)