import threading
import signal
import sys
import time

from dragonfly.log import DFLog
from dragonfly.hardware.dynamixel.dynamixel import Dynamixel_Motor

class FilterTilterError(Exception):
    """Exception raised when a filter tilter error occurs."

    Attributes:
        message - error message
    """
    
    def __init__(self, message:str = "FilterTilter error."):
        self. message = message
        super().__init__(self.message)
    pass


class FilterTilter(object):
    """A Dragonfly FilterTilter Device.  
    """

    def __init__(self, port:str, verbose:bool=False, 
                 path = "/home/dragonfly/dragonfly-arm/active_optics/dcp/dragonfly/hardware/dynamixel/",
                 ms_fn = "state.txt"):
        """Initializes the FilterTilter object.

        Args:
            port (str): Serial port. 
            verbose (bool, optional): Display additional messages. Defaults to False.

        Raises:
            FilterTilterError: Error raised when a filter tilter error occurs.
        """
        self.port = port
        self.verbose = verbose
        
        # Define the state structure. This will get reported on by the get_status() method,
        # which gets periodically called by the polling thread.
        self._state = {}     
        self._state['is_initialized'] = False
        self._state['is_connected'] = False
        self._state['angle'] = None
        self._state['raw_angle'] = None
        self._state['zero_angle'] = None
        
        # You can change these if you really need to... but be careful.
        self._dynamixel_path = path
        self._dynamixel_ms_fn = ms_fn
        self._motor = None

        # Polling
        self._polling_thread = None
        self._polling_interval = 30
        self._polling_enabled = False
        self._stop_polling = threading.Event()
        self._activity_lock = threading.Lock()
        
        # Add signal handler for SIGINT signal
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Add custom logger
        self.logger = DFLog('Filtertilter').logger
        
        self.logger.info("Filter tilter object created.")
        self.logger.info("Motor file path: {}".format(self._dynamixel_path))


    @property
    def state(self):
        """General summary of the state of the DLAPI camera.

        Returns:
            state (dict): Dictionary with state information.
        """
        return self._state
    

    def connect(self):
        """Connects to the FilterTilter.

        Raises:
            FilterTilterError: Error raised if the filter tilter cannot be connected to.
        """
        try:
            self._motor = Dynamixel_Motor(port=self.port, path=self._dynamixel_path, ms_fn=self._dynamixel_ms_fn)
            self._motor.initmotor()
            self._state['is_connected'] = True
            self._state['is_initialized'] = True
            if self._motor.new_statefile == True:
                self.logger.info("New statefile detected. Normalizing filter tilter to approximate values.")
                self.set_raw(180.0)
                self.zero()    
            self.get_status()
            self.logger.info("Filter tilter is connected.")
        except:
            raise FilterTilterError("Error. Could not connect to filter tilter.")   

        
    def disconnect(self):
        """Disconnects from the Filter Tilter.

        Returns:
            string: Returns the string "Filter Tilter disconnected." if successful.
        """
        self.stop_polling()
        self._motor = None # This should call the Dynamixel_Motor destructor.
        self.state['is_connected'] = False
        self.state['is_initialized'] = False
        self.logger.info("Disconnected from Filter Tilter")
        return "Filter Tilter disconnected."     

        
    def _check_connected(self):
        """Checks if the filter tilter is connected. Raises an error if it is not.

        Raises:
            FilterTilterError: Error that occurs when the filter tilter is not connected.
        """
        if not self._state['is_connected']:
            raise FilterTilterError("Error. The filter tilter is not connected.")


    def _signal_handler(self, sig, frame):
        """Signal handler for SIGINT signal."""
        self.stop_polling()  # This also shuts down the polling thread.
        sys.exit(0)
        

    def _poll_refresh_status(self):
        """Function that is executed periodically in a thread to poll the camera information."""
        while not self._stop_polling.is_set():
            self.get_status()
            time.sleep(self._polling_interval)
            if self._stop_polling.is_set():
                break    
        

    def get_status(self):
        """Get general status of the filter tilter.

        Returns:
            state (dict): General status of the filter tilter.
        """
        self._check_connected()
        self.get_raw()
        self.get_zero()
        self.get()
        self.logger.info(f"Filter tilter status: {self._state}")
        return self._state
        

    def get(self):
        """Gets current tilt setting.

        Raises:
            FilterTilterError: Error thrown if the angle cannot be obtained from the filter tilter.
        """
        self._check_connected()
        with self._activity_lock:
            try:
                self._state['angle'] = self._motor.get()
                return(self._state['angle'])
            except:
                raise FilterTilterError("Error. Could not get angle.")

     
    def get_raw(self):
        """Gets current raw tilt setting.

        Raises:
            FilterTilterError: Error thrown if the raw angle cannot be obtained from the filter tilter.
        """
        self._check_connected()
        with self._activity_lock:
            try:
                self._state['raw_angle'] = self._motor.getraw()
                return(self._state['raw_angle'])
            except:
                raise FilterTilterError("Error. Could not get raw angle.")                


    def get_zero(self):
        """Gets zero tilt setting.

        Raises:
            FilterTilterError: Error thrown if the zero angle cannot be obtained from the filter tilter.
        """
        self._check_connected()
        with self._activity_lock:
            try:
                self._state['zero_angle'] = self._motor.getzero()
                return(self._state['zero_angle'])
            except:
                raise FilterTilterError("Error. Could not get zero angle.")


    def zero(self):
        """Sets the current angle of the filter tilter to be the zero angle.

        Raises:
            FilterTilterError: Error thrown if the zero angle cannot be set.
        """
        self._check_connected()
        with self._activity_lock:
            try:
                self._motor.zero()
                info_string = "Filter tilter zero angle set to current angle."
                self.logger.info(info_string)
            except:
                raise FilterTilterError("Error. Could not set zero angle.")
            
            
    def set_zero(self, new_angle:float):
        """Sets the filter tilter zeropoint to be the specified angle in degrees.

        Raises:
            FilterTilterError: Error thrown if the zero angle cannot be set.
        """
        self._check_connected()
        with self._activity_lock:
            try:
                self._motor.setzero(new_angle)
                info_string = f"Filter tilter zero angle set to {new_angle} degrees."
                self.logger.info(info_string)
                return(info_string)
            except:
                raise FilterTilterError("Error. Could not set zero angle.")
            

    def set(self, new_angle:float):
        """Moves the filter tilter to the specified angle in degrees.

        Raises:
            FilterTilterError: Error thrown if the filter tilter cannot be moved to the specified angle.
        """
        self._check_connected()
        with self._activity_lock:
            try:
                self._motor.set(new_angle)
                info_string = f"Filter tilter angle set to {new_angle} degrees."
                self.logger.info(info_string)
                return(info_string)
            except:
                raise FilterTilterError("Error. Could not set filter tilter to the specified angle.")
            

    def set_raw(self, new_angle:float):
        """Moves the filter tilter to the specified raw angle in degrees.

        Raises:
            FilterTilterError: Error thrown if the filter tilter cannot be moved to the specified raw angle.
        """
        self._check_connected()
        with self._activity_lock:
            try:
                self._motor.setraw(new_angle)
                info_string = f"Filter tilter raw angle set to {new_angle} degrees."
                self.logger.info(info_string)
                return(info_string)
            except:
                raise FilterTilterError("Error. Could not set filter tilter to the specified raw angle.")
            
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