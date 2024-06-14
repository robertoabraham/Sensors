import sys
import serial
import time
import threading
import queue
import signal

from dragonfly.log import DFLog

class CanonLensError(Exception):
    """Exception raised when an error occurs with a Canon lens."

    Attributes:
        message - error message
    """

    def __init__(self, message:str = "Lens error."):
        self. message = message
        super().__init__(self.message)
    pass


class CanonLensISError(Exception):
    """Exception raised when an error occurs stabilizing a Canon lens."

    Attributes:
        message - error message
    """
    
    def __init__(self, message:str = "Lens IS error."):
        self. message = message
        super().__init__(self.message)
    pass


class CanonLensCalibrationError(Exception):
    """Exception raised when an error occurs calibrating a Canon lens."

    Attributes:
        message - error message
    """

    def __init__(self, message:str = "Lens calibration error."):
        self. message = message
        super().__init__(self.message)
    pass


class CanonEFLens(object):
    """A Canon EF lens.
    
    To determine the port name, use the following command:
    
      dmesg | grep ttyACM
    
    Look for the line that says something like:
    
      USB ACM device
    
    """

    def __init__(self, port:str="/dev/ttyACM0", verbose:bool=False):
        """Initializes the camera object.

        Args:
            port (string): name of the serial port (e.g. "/dev/ttyUSB0" or "COM1")
            verbose (bool, optional): sets verbose mode on (True) or off (False). Defaults to False.
        """
        self.port = port
        self.verbose = verbose
        
        self.serial = None
        
        self.state = {}
        self.state['is_connected'] = False
        self.state['is_initialized'] = False
        self.state['x'] = None
        self.state['y'] = None
        self.state['z'] = None
        self.state['z_max'] = None
        
        # Use custom logger
        self.logger = DFLog('Canon').logger
        
        # Record the command result
        self._command_result = None
        
        # Allows us to skip checks that we're initialized while actually initializing.
        self._initializing = False
        
        # Polling
        self._polling_thread = None
        self._polling_interval = 5
        self._polling_enabled = False
        self._stop_polling = threading.Event()
        self._activity_lock = threading.Lock()
        
        # Add signal handler for SIGINT signal
        signal.signal(signal.SIGINT, self._signal_handler)

    def __del__(self):
        if self.serial is not None:
            self.serial.close()

    def connect(self):
        """Connects to the self.serial which controls the EF lens.

        Raises:
            CanonLensError: Error raised if the Lens cannot be connected to.

        Returns:
            string: Returns the string "Lens is connected." if successful.
        """
        with self._activity_lock:
            try:
                self.serial = serial.Serial(self.port,
                            baudrate=9600,
                            parity=serial.PARITY_NONE,
                            bytesize=serial.EIGHTBITS,
                            stopbits=serial.STOPBITS_ONE,
                            timeout=1)
                            
                time.sleep(0.5)
                if self.serial.is_open:
                    # result = self._call_with_retry(self._check_lens_presence, (), {})
                    result = "Lens is connected."
                    self.logger.info("Lens is connected.")
                    if "Lens is connected" in result:
                        self.state['is_connected'] = True
                        return "Canon lens connected."
                    else:
                        self.state['is_connected'] = False
                        self.logger.error("Lens is not detected.")
                        raise CanonLensError("Lens is not detected.")
                else:
                    self.state['is_connected'] = False
                    self.logger.error("Could not open the serial port on the Arduino connected to the Canon lens.")
                    raise CanonLensError("Could not open the serial port on the Arduino connected to the Canon lens.")
            except:
                raise CanonLensError("Could not connect to the Canon lens.")

    def _signal_handler(self, sig, frame):
        """Signal handler for SIGINT signal."""
        self.stop_polling()  # This also shuts down the polling thread.
        sys.exit(0)

    def start_polling(self):
        """Starts polling the get_status() method every 30 seconds."""
        if not self._polling_enabled:
            self._polling_enabled = True
            self._stop_polling.clear()
            self._polling_thread = threading.Thread(target=self._poll_refresh_status, daemon=True)
            self._polling_thread.start()
            self.logger.info("Polling started.")

    def stop_polling(self):
        """Stops polling the get_status() method."""
        if self._polling_enabled:
            self._stop_polling.set()
            self._polling_thread.join()
            self._polling_enabled = False
            self.logger.info("Polling stopped.")

    def _poll_refresh_status(self):
        """Function that is executed periodically in a thread to poll the lens information."""
        while not self._stop_polling.is_set():
            self.get_status()
            time.sleep(self._polling_interval)
            if self._stop_polling.is_set():
                break           

    def get_status(self, verbose=False):
        """Returns the status of the lens.

        Returns:
            dict: A dictionary containing the status of the lens.
        """
        try:
            # Grab the activity lock as this method is getting called over and over when we 
            # are polling.
            with self._activity_lock:
                # We need to do this tediously sending individual serial commands, 
                # since the relevant methods grab the activity lock, which we already have.
                
                # Get current focus position.
                focus_command = "pf"
                result = self._run_command(focus_command, verbose)
                focus_position = 0
                try:
                    # _run_command() returns a list containing the communication to and
                    # from the self.serial port. In this case, the relevant line looks like:
                    # 'Focus position: XXXXX' where XXXXX is the number we want.
                    result_line = [line for line in result if 'Focus position:' in line][0]
                    focus_position = int(result_line.split()[-1])
                    self.logger.info("Current focus position: {}".format(focus_position))
                    self.state['z'] = focus_position
                except:
                    self.logger.error("Could not get focus position.")
                    raise CanonLensError

                # Get current IS x-axis and y-axis positions.
                command = "pi"
                lines = self._run_command(command, verbose)
                result_line = lines[-2]
                try:
                    x_position = int(result_line.split()[-5])
                    y_position = int(result_line.split()[-1])
                    self.logger.info("Current IS X,Y position: {},{}".format(x_position, y_position))
                    self.state['x'] = x_position
                    self.state['y'] = y_position
                    self.logger.info(f"IS X,Y position is: {x_position},{y_position}")
                except:
                    raise CanonLensError
                
                self.logger.info(self.state)
                return self.state
        except:
            raise CanonLensError("Could not get lens status.")

    def disconnect(self):
        """Disconnects from a Canon lens.

        Returns:
            string: Returns the string "Lens dis_connected." if successful.
        """
        with self._activity_lock:
            self.state['is_connected'] = False
            self.serial.close()
            self.logger.info("Lens dis_connected.")
            return "Lens dis_connected."

    def initialize(self, verbose=False):
        "Initializes a lens for first use."
        
        # Turn off polling. We'll restart it later if it was on. 
        # The reason we do this is that the initialization process involves
        # calling loads of methods that grab the activity lock. Since the
        # polling thread is also grabbing the activity lock, and since
        # this method takes a long time to execute, it's easiest to just 
        # turn off polling while we're doing this. 
        restart_polling_later = False
        if self._polling_enabled:
            self.stop_polling()
            restart_polling_later = True     
        self._initializing = True
        try:
            results = {}
            
            # Exercise full range
            data = self.learn_focus_range(verbose)
            results['learn'] = data
        
            # Move to nearest focus
            data = self.move_focus_to_closest_focus_position(verbose)
            results['move_near'] = data
                
            # Set lens so 0 ADU is the nearest focus position
            data = self.set_zeropoint(verbose)
            results['zeropoint'] = data
            
            # Move to farthest focus position
            data = self.move_focus_to_infinity(verbose)
            results['move_far'] = data      
                
            # Store the farthest focus position as a state variable. 
            self.logger.info("Recording z_max state variable")  
            pos = int(self.get_focus_position(verbose))
            self.state['z_max'] = pos
            self.state['z'] = pos
                        
            # Zero the IS unit
            pos = self.activate_image_stabilization(verbose)
            self.logger.info("Centering the IS lens.")  
            pos = self.set_is_x_position(0)
            pos = self.set_is_y_position(0)
            [x,y] = self.get_is_position(verbose)
            self.state['x'] = x
            self.state['y'] = y
            
            # Leave the focus roughly near the midpoint.
            self.logger.info("Moving focus to approximate midpoint")
            data = self.set_focus_position(10000, verbose)
            results['move_middle'] = data 
            pos = int(self.get_focus_position(verbose))
            self.state['z'] = pos
            
            self.command_result = results
            self._initializing = False
            
            if restart_polling_later:
                self.start_polling()
            
            # Check if initialization was successful.
            if abs(pos - 10000) < 20:
                self.state['is_initialized'] = True
                self.logger.info("Lens initialized.")
                return "Lens initialized."
            else:
                self.state['is_initialized'] = False                
                self.logger.error("Error. Lens initialization failed.")
                return "Error. Lens initialization failed."      
        except:
            if restart_polling_later:
                self.start_polling()
            self._initializing = False
            raise CanonLensCalibrationError       
        
    def get_focus_position(self, verbose=False):
        "Gets the current focus position on a Canon lens."
        with self._activity_lock:
            focus_command = "pf"
            self.logger.info("Getting focus position.")
            result = self._run_command(focus_command, verbose)
            focus_position = 0
            try:
                # The run_command returns a list containing the communication to and
                # from the self.serial. The relevant line looks like:
                # 'Focus position: XXXXX' where XXXXX is the number we want.
                result_line = [line for line in result if 'Focus position:' in line][0]
                focus_position = int(result_line.split()[-1])
                self.logger.info("Current focus position: {}".format(focus_position))
                self.state['z'] = focus_position
            except:
                self.logger.error("Could not get focus position.")
                raise CanonLensError
            return focus_position

    def set_focus_position(self, focus_value, verbose=False):
        with self._activity_lock:
            "Sets the current focuser position to a specified digital setpoint."
            self.logger.info("Setting focus position to: {}".format(focus_value))
            command = "fa" + str(int(focus_value))
            lines = self._run_command( command, verbose)
            result = lines[-2]
            self.command_result = result
            self.state['z'] = focus_value
            self.logger.info("Focus position set.")
            return "Focus position set."

    def set_is_x_position(self, value, verbose=False):
        "Sets the current IS x-axis position to a specified digital setpoint."
        with self._activity_lock:
            self.logger.info("Setting IS x-axis position to: {}".format(value))
            command = "ix" + str(int(value))
            lines = self._run_command( command, verbose)
            result = lines[-2]
            self.command_result = result
            self.state['x'] = value
            self.logger.info("IS x-axis position set.")
            return "IS x-axis position set."

    def set_is_y_position(self, value, verbose=False):
        "Sets the current IS y-axis position to a specified digital setpoint."
        with self._activity_lock:
            self.logger.info("Setting IS y-axis position to: {}".format(value))
            command = "iy" + str(int(value))
            lines = self._run_command( command, verbose)
            result = lines[-2]
            self.command_result = result
            self.state['y'] = value
            self.logger.info("IS y-axis position set.") 
            return "IS y-axis position set."

    def get_is_position(self, verbose=False):
        "Gets the current focus position on a Canon lens. Returns a list."
        with self._activity_lock:
            command = "pi"
            self.logger.info("Getting IS X-Y position.")
            lines = self._run_command( command, verbose)
            result_line = lines[-2]
            try:
                x_position = int(result_line.split()[-5])
                y_position = int(result_line.split()[-1])
                self.logger.info("Current IS X,Y position: {},{}".format(x_position, y_position))
                self.state['x'] = x_position
                self.state['y'] = y_position
                self.logger.info(f"IS X,Y position is: {x_position},{y_position}")
                return [x_position, y_position]
            except:
                raise CanonLensError

    def activate_image_stabilization(self, verbose=False):
        "Activates the image stabilization system."
        with self._activity_lock:
            command = "is1"
            self.logger.info("Activating image stabilization.")
            lines = self._run_command( command, verbose)
            result = lines[-2]
            self.command_result = result
            self.logger.info("Image stabilization activated.")
            return "Image stabilization activated."

    def deactivate_image_stabilization(self, verbose=False):
        "Activates the image stabilization system."
        with self._activity_lock:
            command = "is0"
            self.logger.info("Deactivating image stabilization.")
            lines = self._run_command( command, verbose)
            result = lines[-2]
            self.command_result = result
            self.logger.info("Image stabilization deactivated.")
            return "Image stabilization deactivated."

    def open_aperture(self, verbose=False):
        "Fully opens lens aperture."
        with self._activity_lock:
            command = "in"
            self.logger.info("Opening lens aperture.")
            lines = self._run_command( command, verbose)
            result = lines[-2]
            self.command_result = result
            self.logger.info("Lens aperture opened.")
            return "Lens aperture opened."

    def move_focus_to_infinity(self, verbose=False):
        "Focuses lens to infinity."
        with self._activity_lock:
            command = "mi"
            self.logger.info("Moving lens to infinity focus.")
            lines = self._run_command( command, verbose)
            result = lines[-2]
            self.command_result = result
            self.logger.info("Lens focused to infinity.")
            return "Lens focused to infinity."

    def move_focus_to_closest_focus_position(self, verbose=False):
        "Focuses lens to closest focus position."
        with self._activity_lock:
            command = "mz"
            self.logger.info("Moving lens to closest focus position.")
            lines = self._run_command( command, verbose)
            result = lines[-2]
            self.command_result = result
            self.logger.info("Lens focused to closest focus position.")
            return "Lens focused to closest focus position."

    def learn_focus_range(self, verbose=False):
        "Calibrates lens focus range (minimum and maximum setpoints)"
        with self._activity_lock:
            command = "la"
            self.logger.info("Calibrating lens focus range")
            lines = self._run_command( command, verbose)
            result = lines[-2]
            self.command_result = result
            self.logger.info("Lens focus range learned.")
            return "Focus range learned."

    def set_zeropoint(self, verbose=False):
        "Sets the minimum position of the lens to be zero"
        with self._activity_lock:
            command = "sf0"
            self.logger.info("Setting lens zeropoint")
            lines = self._run_command( command, verbose)
            result = lines[-2]
            self.command_result = result
            self.logger.info("Lens zeropoint set.")
            return "Zeropoint set."

    def _check_lens_presence(self, verbose=False):
        with self._activity_lock:
            "Returns a string indicating whether or not a lens is connected."
            command = "lp"
            self.logger.info("Checking for lens presence.")
            lines = self._run_command(command, verbose)
            # The last line returned by the self.serial is always "Received: Done." so the line 
            # with the useful information is always the second to the last line.
            result = lines[-2]
            self.command_result = result
            self.logger.info("Lens presence checked. Result: {}".format(result))
            return result

    def _run_command(self, command, verbose=False, super_verbose=False):
        "Runs a low-level lens command on the lens via the Arduino's serial port."
        if command is not None:
            command = command + '\n'
            command = command.lower()
            self.serial.flush()
            self.serial.write(command.encode())
            line = ""
            lines = []
            self.logger.info("Sending command: {}".format(command.rstrip()))
            while(True):
                if self.serial.in_waiting >0:
                    time.sleep(0.01)
                    c = self.serial.read().decode()
                    if c == '\n':
                        lines.append(line.lstrip().rstrip())
                        if super_verbose:
                            print("  Received: {}".format(line.lstrip().rstrip()))
                        if "Done" in line:
                            break
                        line = ""
                    line = line + c
            #result = lines[-2].lstrip().rstrip()
            #self.logger.info("Result: {}\n".format(result))
            self.serial.flush()
            if verbose:
                self.logger.info("Result: {}\n".format(lines))
            #return result
            return(lines)
