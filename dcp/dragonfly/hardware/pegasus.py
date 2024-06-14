import serial
import time
import pprint
import logging
import threading
import signal
import sys

from dragonfly.find import find_powerbox_serial_port
from dragonfly.log import DFLog

class PegasusPowerboxError(Exception):
    """Exception raised when an error occurs in a Pegasus Powerbox."

    Attributes:
        message - error message
    """

    def __init__(self, message:str = "Powerbox error.", custom_field:str = '[PegasusPowerbox]'):
        self. message = message
        self.logger = DFLog('PegasusPowerbox').logger
            
        self.logger.error(self.message)
        super().__init__(self.message)
    pass


class PegasusPowerbox(object):
    """A Pegasus Powerbox.
    
    To determine the port name, use the following command:
    
      dmesg | grep ttyUSB
    """
    
    def __init__(self, port:str="/dev/ttyUSB0", verbose:bool=False):
        """Initializes the PegasusPowerbox object.
        """
        self.port = port
        self.verbose = verbose
        self.serial = None
        
        self._state = {}
        self._state['is_connected'] = False
        self._state["input_voltage"] = None
        self._state["current_amps"] = None
        self._state["temperature_c"] = None
        self._state["humidity_pct"] = None
        self._state["dewpoint_c"] = None
        self._state["quadport_is_on"] = None
        self._state["adjustable_port_is_on"] = None
        self._state["adjustable_port_voltage"] = None
        self._state["duty_cycle_a"] = None
        self._state["duty_cycle_b"] = None
        self._state["autodew_on"] = None
        self._state["power_warning"] = None
        
        self.logger = DFLog('PegasusPowerbox').logger
        self.command_running = False
        
        self._polling_thread = None
        self._polling_interval = 5
        self._polling_enabled = False
        self._stop_polling = threading.Event()
        self._activity_lock = threading.Lock()
        
        # Add signal handler for SIGINT signal
        signal.signal(signal.SIGINT, self._signal_handler)


    @property
    def state(self):
        return self._state
    
    
    def __del__(self):
        """Destructor for the PegasusPowerbox object."""
        if self.serial is not None:
            self.serial.close()
        if self._polling_enabled:
            self.stop_polling()
            
        self._remove_root_logger_stream_handler()
        self.logger.info("Pegasus Powerbox object deallocated.")

        
    def _remove_root_logger_stream_handler(self):
        """Removes the StreamHandler from the root logger."""
        # This method is needed because if a method is called from a background
        # thread it sometimes doesn't seem to inherit the logging configuration,
        # and I get log messages printed twice. This method removes the StreamHandler
        # so that the log messages are only printed to the FileHandler.
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                root_logger.removeHandler(handler)

    def _signal_handler(self, sig, frame):
        """Signal handler for SIGINT signal."""
        self.stop_polling() # This also shuts down the polling thread.
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
        """Function that is executed periodically in a thread to poll the powerbox information."""
        while not self._stop_polling.is_set():
            self._remove_root_logger_stream_handler()
            with self._activity_lock:
                self._refresh_status()
            time.sleep(self._polling_interval)
            if self._stop_polling.is_set():
                break           
            
    def _refresh_status(self):
        "Polls the power controller for information"
        self.logger.info("Getting power controller state.")
        powerbox_command = "PA"
        result = self.run_command(powerbox_command)
        (dummy,v,c,t,h,dp,qp,ao,d1p,d2p,ad,pwn,padj) = result[0].rstrip().split(":")
        self._state["input_voltage"] = float(v)
        self._state["current_amps"] = round(float(c)/65,3)
        self._state["temperature_c"] = float(t)
        self._state["humidity_pct"] = float(h)
        self._state["dewpoint_c"] = float(dp)
        if qp == "0":
            self._state["quadport_is_on"] = False
        else:
            self._state["quadport_is_on"] = True
        if ao == "0":
            self._state["adjustable_port_is_on"] = False
        else:
            self._state["adjustable_port_is_on"] = True
        self._state["adjustable_port_voltage"] = float(padj)
        self._state["duty_cycle_a"] = int(d1p)
        self._state["duty_cycle_b"] = int(d2p)
        if ad == "0":
            self._state["autodew_on"] = False
        else:
            self._state["autodew_on"] = True
        if pwn == "0":
            self._state["power_warning"] = False
        else:
            self._state["power_warning"] = True                    
        if "ERR" in result[0]:
            raise PegasusPowerboxError("Could not get Powerbox state.")
        
        self._remove_root_logger_stream_handler()
        self.logger.info(self.state)


    def connect(self):
        """Connects to the Pegasus Powerbox.

        Raises:
            PegasusPowerboxError: Error raised if the Powerbox cannot be connected to.

        Returns:
            string: Returns the string "Pegasus Powerbox connected." if successful.
        """
        try:
            self.serial = serial.Serial(self.port,
                        baudrate=9600,
                        parity=serial.PARITY_NONE,
                        bytesize=serial.EIGHTBITS,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1)
            time.sleep(0.5)
            if self.serial.is_open:
                self.state['is_connected'] = True
                self.logger.info(f"Connected to Pegasus Powerbox on port {self.port}")
                return "Pegasus Powerbox connected."
            else:
                self.state['is_connected'] = False
                raise PegasusPowerboxError(f"Could not connect to Pegasus Powerbox on port {self.port}")
        except:
            raise PegasusPowerboxError(f"Could not connect to Pegasus Powerbox on port {self.port}")


    def disconnect(self):
        """Disconnects from the Pegasus Powerbox.

        Returns:
            string: Returns the string "Pegasus Powerbox disconnected." if successful.
        """
        self.stop_polling()
        self.state['is_connected'] = False
        self.serial.close()
        self.logger.info("Disconnected from Pegasus Powerbox")
        return "Pegasus Powerbox disconnected."
            
                
    def quadport_on(self):
        "Turns the power controller on."
        self.logger.info("Turning the power controller on.")
        powerbox_command = "P1:1"
        result = self.run_command(powerbox_command)
        if "ERR" in result[0]:
            raise PegasusPowerboxError("Could not turn the power controller on.")
        self.logger.info("Quadport power on.")
        return "Quadport on."


    def quadport_off(self):
        "Turns the power controller off."
        self.logger.info("Turning the power controller off.")
        powerbox_command = "P1:0"
        result = self.run_command(powerbox_command)
        if "ERR" in result[0]:
            raise PegasusPowerboxError("Could not turn the power controller off.")
        self.logger.info("Quadport power off.")
        return "Quadport off."


    def adjport_on(self):
        "Turns the power controller on."
        self.logger.info("Turning the power controller on.")
        powerbox_command = "P2:1"
        result = self.run_command(powerbox_command)
        if "ERR" in result[0]:
            raise PegasusPowerboxError("Could not turn the adjustable port on.")
        self.logger.info("Adjustable port power on.")
        return "Adjustable port on."


    def adjport_off(self):
        "Turns the power controller off."
        self.logger.info("Turning the power controller off.")
        powerbox_command = "P2:0"
        result = self.run_command(powerbox_command)
        if "ERR" in result[0]:
            raise PegasusPowerboxError("Could not turn the adjustable port off.")
        self.logger.info("Adjustable port power off.")
        return "Adjustable port off."

        
    def get_status(self):
        """Report camera status.

        Returns: 
            dict: A dictionary containing the camera status.
        
        """
        self._refresh_status()
        return self.state     


    def run_command(self, command, verbose=False):
        "Runs a low-level power controller command."
                
        # If a command is already running (presumably started in a background thread)
        # wait until it is finished before running the next command.
        n_wait = 0
        max_wait = 10
        while self.command_running:
            self.logger.error("Command already running. Waiting 0.5s for command to finish.")
            time.sleep(0.5)
            n_wait = n_wait + 1
            if n_wait >= max_wait:
                raise PegasusPowerboxError("Timed out. Could not run command as the previous command did not complete (waited 5s).")
            
        if command is not None:
            self.command_running = True
            command = command + '\n'
            command = command.upper()
            try:
                self.serial.flush()
                self.serial.write(command.encode())
                line = ""
                lines = []
                while True:
                    if self.serial.inWaiting() > 0:
                        time.sleep(0.01)
                        c = self.serial.read().decode()
                        if c == '\n':
                            lines.append(line)
                            if verbose:
                                print("  Received: {}".format(line.lstrip().rstrip()))
                            break
                        line = line + c
                self.serial.flush()
                self.command_running = False
                return lines 
            except:
                self.command_running = False
                raise PegasusPowerboxError("Could not run command.")
        
def demo():
    pp = pprint.PrettyPrinter(indent=2)
    print('Searching for powerbox.')
    serial_port = find_powerbox_serial_port()
    print(f'Powerbox found on port: {serial_port}')
    print('Creating a PegasusPowerbox() object.')
    pb = PegasusPowerbox(serial_port, verbose=False)
    print('Connecting to the powerbox.')
    pb.connect()
    print('Getting status of the powerbox:')
    data = pb.get_status()
    pp.pprint(data)
    print('Disconnecting from the powerbox.')
    pb.disconnect()