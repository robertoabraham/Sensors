# TESTED ON A RASPBERRY PI RUNNING ARM64 LINUX AND ON A PC RUNNING
# MS-WINDOWS 11 ON AN INTEL ARCHITECTURE.

# 1. Careful! Need to use the right USB-Serial Adapter!
#
# With a Raspberry Pi running Linux ARM 64 this works with an adapter
# that has the Prolific chipset, but not with a Tripp-Lite (Keyspan)
# adapter. I think the support for random USB-Serial converters
# on Linux ARM 64 is not there.
#
# 2. AP Protocol "gotchas"
#
# Some mount commands return nothing, some mount commands return a
# string ending in "#", and some mount commands return single characters
# which may or may not have a "#" terminator. Read the documentation
# supplied by Astro-Physics carefully to figure out what a particular
# command returns, and set the _response_type_ argument to the _send_
# command appropriately to handle these different cases.

import time
import logging
import serial
import re
import sys
import threading
import signal
import pprint

from astropy import units as u
from astropy.coordinates import SkyCoord

from dragonfly.site import ObservingSite
from dragonfly.log import DFLog
from dragonfly.improc import plate_solve
from dragonfly.find import find_mount_serial_port

# Utility functions

def ap_radec_to_deg(ra: str, dec: str) -> list[float]:
    """Convert from Astro-Physics strings to decimal degrees.

    Args:
        ra (string): String in Astro-Physics 'HH:MM:SS.S' format
        dec (string): String in Astro-Physics 'sDD*MM:SS' format

    Returns:
        list: [ra, dec] in floating point degrees (0-360, -90-90)
    """
    pyra = re.sub(r'^(.*):(.*):(.*)', r'\1h\2m\3s', ra)
    pydec = re.sub(r'^([+-])(.*)\*(.*):(.*)', r'\1\2d\3m\4s', dec)
    c = SkyCoord(pyra, pydec, frame='icrs')
    return [c.ra.degree, c.dec.degree]


def ap_altaz_to_deg(ap_alt: str, ap_az: str) -> list[float]:
    """Convert from Astro-Physics Alt-Az strings to decimal degrees.

    Args:
        ra (string): String in Astro-Physics 'HH:MM:SS.S' format
        dec (string): String in Astro-Physics 'sDD*MM:SS' format

    Returns:
        list: [ra, dec] in floating point degrees (0-360, -90-90)
    """
    # The bit below is a bit gruesome... we use the routines built in 
    # to SkyCoord to pretend our Alt-Az coordinates are RA-Dec coordinates.
    # so we can hijack its methods for parsing the strings and turning
    # them into degrees. We also have to input az, alt rather than
    # alt, az to get round domain range limits in the SkyCoord routines.
    pyalt = re.sub(r'^([+-])(.*)\*(.*):(.*)', r'\1\2d\3m\4s', ap_alt)
    pyaz = re.sub(r'^([+-])(.*)\*(.*):(.*)', r'\1\2d\3m\4s', ap_az)
    c = SkyCoord(pyaz, pyalt, frame='icrs')
    return [c.dec.degree, c.ra.degree]


def deg_to_ap_radec(ra: float, dec: float) -> list[str]:
    """Convert from decimal degrees to Astro-Physics strings.

    Args:
        ra (float): right ascension in degrees (0 - 360)
        dec (float): declination in degrees (-90, 90)

    Returns:
        list: ['HH:MM:SS.s', 'sDD*MM:SS']
    """
    c = SkyCoord(ra*u.deg, dec*u.deg)
    cs = c.to_string('hmsdms')
    [ras, decs] = cs.split()

    # Remove excess precision.
    decs = re.sub(r'^(.*)\.(\d*)', r'\1', decs)
    ras = re.sub(r'^(.*\.)(\d)(\d*)', r'\1\2', ras)

    # Reformat
    decs = re.sub(r'^(.*)d(.*)m(.*)s', r'\1*\2:\3', decs)
    ras = re.sub(r'^(.*)h(.*)m(.*)s', r'\1:\2:\3', ras)

    return [ras, decs]


def skycoord_to_ap_radec(c: SkyCoord) -> list[str]:
    """Convert from AstroPy SkyCoord to Astro-Physics [RA, Dec] strings.

    Args:
        c (SkyCoord): AstroPy sky coordinate

    Returns:
        list: ['HH:MM:SS.s', 'sDD*MM:SS']
    """
    cs = c.to_string('hmsdms')
    [ras, decs] = cs.split()

    # Remove excess precision.
    ras = re.sub(r'^(.*\.)(\d)(\d*)', r'\1\2', ras)
    decs = re.sub(r'^(.*)\.(\d*)', r'\1', decs)

    # Reformat
    ras = re.sub(r'^(.*)h(.*)m(.*)s', r'\1:\2:\3', ras)
    decs = re.sub(r'^(.*)d(.*)m(.*)s', r'\1*\2:\3', decs)

    return [ras, decs]

# Exception classes


class APMountError(Exception):
    """Exception raised when an error occurs when trying to control a mount."

    Attributes:
        message - error message
    """

    def __init__(self, message:str = "Powerbox error.", custom_field:str = '[PegasusPowerbox]'):
        self. message = message
        self.logger = DFLog('AstroPhysics').logger
        self._remove_root_logger_stream_handler()      
        self.logger.error(self.message)
        super().__init__(self.message)
    pass


# The main class

class GTOControlBox(object):
    """An Astro-Physics GTO mount control box."""

    def __init__(self, port:str, verbose:bool=False):
        """Initializes the mount object.

        Args:
            port (string): name of the serial port (e.g. "/dev/ttyUSB0" or "COM1")
            verbose (bool, optional): sets verbose mode on (True) or off (False). Defaults to False.
        """
        self.port = port
        self.verbose = verbose
        self.serial = None
        self.logger = DFLog('AstroPhysics').logger 
        
        self.status = {}
        self.status['is_connected'] = False
        self.status['is_slewing'] = False
        self.status['ra'] = None
        self.status['dec'] = None
        self.status['alt'] = None
        self.status['az'] = None
        self.status['pier_side'] = None
        self.status['latitude'] = None
        self.status['longitude'] = None
        self.status['gmt_offset'] = None 
            
        self.command_running = False
        
        self._polling_thread = None
        self._polling_interval = 30
        self._polling_enabled = False
        self._stop_polling = threading.Event()
        self._activity_lock = threading.Lock()
        
        # Add signal handler for SIGINT signal
        signal.signal(signal.SIGINT, self._signal_handler)
            
        self.logger.info("Mount initialized.")

    def __del__(self):
        self.stop_polling()
        if self.serial is not None:
            self.serial.close()

    def connect(self):
        """Connects to an Astro-Physics telescope mount.

        Raises:
            APMountError: Error raised if the mount cannot be connected to.

        Returns:
            string: Returns the string "Mount connected." if successful.
        """
        try:

            if sys.platform == 'linux':
                # The following settings appear to work well with a Prolific chip serial port
                # adapter, but not with a Tripp-Lite (Keyspan) serial port adapter. I'm fairly
                # sure the ARM64 Linux driver for the Keyspan USB-Serial adapters is buggy.
                self.serial = serial.Serial(self.port,
                                            baudrate=9600,
                                            parity=serial.PARITY_NONE,
                                            bytesize=serial.EIGHTBITS,
                                            stopbits=serial.STOPBITS_ONE,
                                            rtscts=0,     # Hardware handshaking. Puts CTS_HANDSHAKE in ControlHandshake()
                                            xonxoff=0,    # Software handshking. Puts AUTO_TRANSMIT, AUTO_RECEIVE in FlowReplace()
                                            dsrdtr=0      # ControlHandshake. 0 = DTR_CONTROL
                                            )
                time.sleep(0.5)
                self.serial.dtr = True
                self.serial.rts = False
                self.status['is_connected'] = True
                self.logger.info("Connected to mount.")

            else:
                self.serial = serial.Serial(self.port,
                                            baudrate=9600,
                                            parity=serial.PARITY_NONE,
                                            bytesize=serial.EIGHTBITS,
                                            stopbits=serial.STOPBITS_ONE,
                                            rtscts=0,     # Hardware handshaking. Puts CTS_HANDSHAKE in ControlHandshake()
                                            xonxoff=0,    # Software handshking. Puts AUTO_TRANSMIT, AUTO_RECEIVE in FlowReplace()
                                            dsrdtr=0,     # ControlHandshake. 0 = DTR_CONTROL
                                            write_timeout=0.2,
                                            timeout=0.2
                                            )
                time.sleep(0.5)
                # This sets the in/out queue size, so it matches what I see when I sniff the
                # serial packets sent by the AP ASCOM driver in Windows.
                self.serial.set_buffer_size(rx_size=4096, tx_size=2048)
                self.serial.dtr = True
                self.serial.rts = False
                self.status['is_connected'] = True
                self.logger.info("Connected to mount.")


            # Allow half a second to make sure the serial port is properly opened.
            time.sleep(0.5)

            # Clear the command buffer.
            self.send("#", response_type=None)
            time.sleep(0.2)

            # Set long format output mode.
            self.send(":U#", response_type=None)
            time.sleep(0.2)
            
            # Store mount position and location.
            self.location()
            self.position()

            return "Mount connected."
        except:
            raise APMountError()


    def disconnect(self):
        """Disconnects from an Astro-Physics telescope mount.

        Returns:
            string: Returns the string "Mount disconnected." if successful.
        """
        self.status['is_connected'] = False
        self.stop_polling()
        self.serial.close()
        self.logger.info("Disconnected from mount.")
        return "Mount disconnected."


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

            
    def _poll_refresh_position(self):
        """Function that is executed periodically in a thread to poll the mount position."""
        while not self._stop_polling.is_set():
            self._remove_root_logger_stream_handler()
            with self._activity_lock:
                self._get_position()
            time.sleep(self._polling_interval)
            if self._stop_polling.is_set():
                break

    def position(self):
        """Returns the current position of the mount."""
        with self._activity_lock:
            data = self._get_position()
            output = {}
            output['ra'] = data[0]
            output['dec'] = data[1]
            output['alt'] = data[2]
            output['az'] = data[3]
            output['pier_side'] = data[4]
            return output

    def _get_position(self):
        """Helper method that retrieves the current position of the mount."""
 
        # Get RA
        if self.verbose:
            print("Getting R.A.")
        ra = self.send(":GR#")
        time.sleep(0.1)

        # Get Dec
        if self.verbose:
            print("Getting Dec.")
        dec = self.send(":GD#")
        time.sleep(0.1)

        # Get Alt
        if self.verbose:
            print("Getting Alt.")
        altitude = self.send(":GA#")
        time.sleep(0.1)

        # Get Az
        if self.verbose:
            print("Getting Az.")
        azimuth = self.send(":GZ#")
        time.sleep(0.1)

        # Pier side
        if self.verbose:
            print("Pier side.")
        pier_side = self.send(":pS#")
        time.sleep(0.1)
        
        self.status['ra'] = ra
        self.status['dec'] = dec
        self.status['alt'] = altitude
        self.status['az'] = azimuth
        self.status['pier_side'] = pier_side
        
        self._remove_root_logger_stream_handler()
        self.logger.info(self.status)
        return ra, dec, altitude, azimuth, pier_side            
            
    def _signal_handler(self, sig, frame):
        """Signal handler for SIGINT signal."""
        self.stop_polling() # This also shuts down the polling thread.
        sys.exit(0)
        
    def start_polling(self):
        """Starts polling the get_status() method every 30 seconds."""
        if not self._polling_enabled:
            self._polling_enabled = True
            self._stop_polling.clear()
            self._polling_thread = threading.Thread(target=self._poll_refresh_position, daemon=True)
            self._polling_thread.start()
            self.logger.info("Polling started.")


    def stop_polling(self):
        """Stops polling the get_status() method."""
        if self._polling_enabled:
            self._stop_polling.set()
            self._polling_thread.join()
            self._polling_enabled = False
            self.logger.info("Polling stopped.")
            

    def send(self, command:str, wait_time:float=0.2, response_type:str="string"):
        """Sends a serial command to an Astro-Physics telescope mount.

        Args:
            command (string):  Valid Astro-Physics mount serial command.
            response_type (str, optional): "string", "char" or None. Defaults to "string".

        Raises:
            APMountError: error message describing the problem that has occurred.

        Returns:
            a string, a char or None: returned by the serial command.
        """

        # Make sure we know what kind of response is expected!
        if response_type == None or response_type == "string" or response_type == "char":
            pass
        else:
            raise APMountError(f"Unknown reponse type ({response_type})")

        cmd = command.encode()
        if self.verbose:
            print(f"Sending: {cmd}")
        try:
            self.serial.reset_input_buffer()
            self.serial.write(cmd)
            time.sleep(wait_time)
        except AttributeError:
            raise APMountError("Could not send command. Are you connected?")

        if response_type == None:
            return None

        elif response_type == "char":
            c = self.serial.read().decode()
            if self.verbose:
                print(f"Got: {c}")
            self.serial.flush()
            return c

        elif response_type == "string":
            response = ""
            while (True):
                c = self.serial.read().decode()
                if self.verbose:
                    print(f"Got: {c}")
                if c == '#':
                    break
                response = response + c
                time.sleep(0.01)
            self.serial.flush()
            return response

        else:
            raise APMountError("Unknown response type")


    def _get_char(self):
        """Gets a single character from the mount. (Debugging command) 

        Returns:
            string: single character returned by the mount.
        """
        c = self.serial.read().decode()
        if self.verbose:
            print(f"Got: {c}")
        return c


    def _clear(self):
        """Clears the mount's input and output buffers.
        """
        if self.serial is not None:
            self.serial.flush()
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
        else:
            print("Not connected.")


    def _in_waiting(self):
        """Number of bytes in the mount's input buffer.

        Raises:
            APMountError: raises this exception if mount is not connected

        Returns:
            int: number of bytes in the buffer
        """
        if self.serial is not None:
            return self.serial.in_waiting
        else:
            raise APMountError("Not connected.")


    def _out_waiting(self):
        """Number of bytes in the mount's output buffer.

        Raises:
            APMountError: raises this exception if mount is not connected

        Returns:
            int: number of bytes in the buffer
        """
        if self.serial is not None:
            return self.serial.out_waiting
        else:
            raise APMountError("Not connected.")


    def update_mount_settings(self, location:ObservingSite):
        """Updates the mount's flash storage with location and time information.

        Args:
            location (ObservingSite): An instance of a Dragonfly ObservingSite object.

        Raises:
            APMountError: Error raised if the location argument is not a GeographicalLocation object.

        Example:
            from dragonfly import apmount
            from dragonfly.site import oakville

            gto = apmount.GTOControlBox("/dev/ttyUSB0")
            gto.connect()
            gto.update_mount_settings(oakville)    
        """
        if type(location) is not ObservingSite:
            raise APMountError(
                "location argument must be an ObservingSite object.")
        data = location.data_in_astro_physics_mount_format()
        print("Setting latitude")
        self.set_latitude(data['latitude'])
        print("Setting longitude")
        self.set_longitude(data['longitude'])
        print("Setting local time")
        self.set_local_time(data['local_time'])
        print("Setting date")
        self.set_date(data['date'])
        print("Setting GMT offset")
        self.set_gmt_offset(data['gmt_offset'])
        
        self.status['latitude'] = data['latitude']
        self.status['longitude'] = data['longitude']
        self.status['date'] = data['date']
        self.status['local_time'] = data['local_time']
        self.status['gmt_offset'] = data['gmt_offset']
        
        self.logger.info("Mount settings updated.")


    def set_longitude(self, longitude:str):
        """Sets the longitude in an Astro-Physics GTO mount.

        Args:
            longitude (string): Longitude as a string in "DDD*MM:SS" format.

        Returns:
            char: returns "1" on success.
        """
        with self._activity_lock:
            response = self.send(f":Sg {longitude}#", response_type="char")
            self.logger.info(f"Longitude set to {longitude}")
            return response


    def set_latitude(self, latitude:str):
        """Sets the latitude in an Astro-Physics GTO mount.

        Args:
            latitude (string): Latitude as a string in "sDD*MM:SS" format.

        Returns:
            char: returns "1" on success.
        """
        with self._activity_lock:
            response = self.send(f":St {latitude}#", response_type="char")
            self.logger.info(f"Latitude set to {latitude}")
            return response


    def set_local_time(self, local_time:str="now"):
        """Sets the local time in an Astro-Physics GTO mount.

        Args:
            local_time (string): Time as a string in "HH:MM:SS" format, or "now".

        Returns:
            char: returns "1" on success.
        """
        if local_time == "now":
            local_time = time.strftime("%H:%M:%S", time.localtime())
        with self._activity_lock:
            response = self.send(f":SL {local_time}#", response_type="char")
        self.logger.info(f"Local time set to {local_time}")
        return response


    def set_date(self, date:str="today"):
        """Sets the date in an Astro-Physics GTO mount.

        Args:
            date (string): Date as a string in "MM/DD/YY" format.

        Returns:
            char: success returns a string with 32 spaces.
        """
        if date == "today":
            date = time.strftime("%m/%d/%y", time.localtime())
        with self._activity_lock:
            response = self.send(f":SC {date}#", response_type="string")
            self.logger.info(f"Date set to {date}")
            return response


    def set_gmt_offset(self, gmt_offset:str):
        """Sets the GMT offset in an Astro-Physics GTO mount.

        Args:
            gmt_offset (string): Offset in either "sHH" or "sHH:MM" or "sHH:MM:SS" format.

        Returns:
            char: returns "1" on success.
        """
        with self._activity_lock:
            response = self.send(f":SG {gmt_offset}#", response_type="char")
            self.logger.info(f"GMT offset set to {gmt_offset}")
            return response


    def location(self):
        """Summarizes mount location information in a Python dictionary.

        Returns:
            dict: Dict with keys 'latitude', 'longitude', 'date', 'local_time', 'sidereal_time', 'gmt_offset'
        """
        with self._activity_lock:
            
            # Get latitude
            if self.verbose:
                print("Getting latitude")
            latitude = self.send(":Gt#")
            time.sleep(0.1)

            # Get longitude
            if self.verbose:
                print("Getting longitude")
            longitude = self.send(":Gg#")
            time.sleep(0.1)

            # Get date
            if self.verbose:
                print("Getting date")
            date = self.send(":GC#")
            time.sleep(0.1)

            # Get local time
            if self.verbose:
                print("Getting local time")
            local_time = self.send(":GL#")
            time.sleep(0.1)

            # Get GMT offset
            if self.verbose:
                print("Getting longitude")
            gmt_offset = self.send(":GG#")
            time.sleep(0.1)

            # Get sidereal time
            if self.verbose:
                print("Getting sidereal time")
            sidereal_time = self.send(":GS#")
            time.sleep(0.1)
        
        self.status['latitude'] = latitude
        self.status['longitude'] = longitude
        self.status['gmt_offset'] = gmt_offset
        
        info = {}
        info['latitude'] = latitude
        info['longitude'] = longitude
        info['date'] = date
        info['local_time'] = local_time
        info['gmt_offset'] = gmt_offset
        info['sidereal_time'] = sidereal_time
        self.logger.info(f"Mount location: Latitude = {latitude}, Longitude = {longitude}, Date = {date}, Local time = {local_time}, GMT offset = {gmt_offset}, Sidereal time = {sidereal_time}")

        return info


    def sync(self, ra:str, dec:str, resync:bool=False):
        """Synchronize the mount to the specified position.

        Args:
            ra (string): Right ascension in sexagesimal (HH:MM:SS.S) notation
            dec (string): Declination in sexagesimal (sDD*MM:SS.S) notation
            resync (bool, optional): Do a resync instead of a sync. See manual for details (default = False)
        """

        with self._activity_lock:
            result = self.send(f"#:Sr {ra}#", response_type="char")
            if result != "1":
                raise APMountError("Could not set RA for sync command.")
            time.sleep(0.5)

            result = self.send(f"#:Sd {dec}#", response_type="char")
            if result != "1":
                raise APMountError("Could not set Dec for sync command.")
            time.sleep(0.5)

            if resync:
                result = self.send("#:CM#")
            else:
                result = self.send("#:CMR#")

        if not "matched" in result:
            raise APMountError("Sync not accepted.")
        
        self.status['ra'] = ra
        self.status['dec'] = dec
        
        self.logger.info(f"Synced to RA = {ra}, Dec = {dec}")
        
        return (result)


    def sync_to_target(self, name:str, resync:bool=False):
        """Syncs the mount to the specified object.

        Args:
            name (string): Named celestial object (e.g. "Deneb" or "M31")
            resync (bool, optional): Do a "resync" instead of a "sync". See AP manual. Defaults to False.

        Returns:
            string: Returns a string containing "Coordinates matched." if successful.
        """
        if self.verbose:
            print(f"Getting coordinates of {name} from CDS.")
        c = SkyCoord.from_name(name)
        [apra, apdec] = skycoord_to_ap_radec(c)
        print(f"Syncing to {apra} {apdec}")
        result = self.sync(apra, apdec, resync=resync)
        self.logger.info(f"Synced to target {name}")
        return result


    def sync_to_image(self, fits_filename:str, resync:bool=False):
        """Syncs the mount to the specified object.

        Args:
            fits_filename (string): path to FITS filename.
            resync (bool, optional): Do a "resync" instead of a "sync". See AP manual. Defaults to False.

        Returns:
            string: Returns a string containing "Coordinates matched." if successful.
        """
        solution = plate_solve(fits_filename)
        if solution['Success'] == True:
            ra = solution['RA']
            dec = solution['Dec']
            [ra, dec] = deg_to_ap_radec(ra, dec)
            result = self.sync(ra, dec, resync=resync)
            self.logger.info(f"Synced to image {fits_filename}")
            return result
        else:
            raise APMountError("Plate solve failed.")


    def target_distance(self, ra_target:str, dec_target:str):
        """Distance to target in degrees.

        Args:
            ra_target (string): RA in AP string format (HH:MM:SS.S).
            dec_target (string): Dec in AP string format (sDD*MM:SS.S).

        Returns:
            _type_: _description_
        """

        # Store the current position and the target position as SkyCoord objects.
        current = self.position()
        ra_current = current['ra']
        dec_current = current['dec']
        [ra_current_deg, dec_current_deg] = ap_radec_to_deg(ra_current, dec_current)
        c_current = SkyCoord(ra_current_deg*u.deg, dec_current_deg*u.deg)

        [ra_target_deg, dec_target_deg] = ap_radec_to_deg(ra_target, dec_target)
        c_target = SkyCoord(ra_target_deg*u.deg, dec_target_deg*u.deg)

        # Determine separation to target in degrees.
        separation = SkyCoord.separation(c_current, c_target)
        separation_deg = separation.degree
        
        return separation_deg

    def slew(self, ra:str, dec:str, wait:bool=True):
        """Slew the mount to the specified position.

        Args:
            ra (string): Right ascension in sexagesimal (HH:MM:SS.S) notation
            dec (string): Declination in sexagesimal (sDD*MM:SS.S) notation
            wait (bool, optional): Blocks until slew is completed. Defaults to False.
        """

        with self._activity_lock:
            result = self.send(f"#:Sr {ra}#", response_type="char")
            if result != "1":
                raise APMountError("Could not set RA for sync command.")
            time.sleep(0.5)

            result = self.send(f"#:Sd {dec}#", response_type="char")
            if result != "1":
                raise APMountError("Could not set Dec for sync command.")
            time.sleep(0.5)

            result = self.send("#:MS#", response_type="char")
            if not "0" in result:
                raise APMountError("Slew error.")
            
            self.status['is_slewing'] = True
            self.logger.info(f"Slewing to RA = {ra}, Dec = {dec}")

        if wait:
            time.sleep(1)
            distance = 10000.0
            # Wait until we are within 10 arcmin of the target.
            while distance > (600.0/3600.0):
                distance = self.target_distance(ra, dec)
                print(f"Distance to target: {round(distance,3)} deg.      ", end="\r")
                time.sleep(1)
            self.status['is_slewing'] = False
            print("")
            self.logger.info("Slew complete.")
            return "Slew complete."
        else:
            self.logger.info("Slew is asynchronous. The user is responsible checking when it is done.")
            return "Slew begun."

    def slew_to_target(self, name:str, wait:bool=True):
        """Slews the mount to the specified target.

        Args:
            name (string): Named celestial object (e.g. "Deneb" or "M31")
            wait (bool, optional): Blocks until slew is completed. Defaults to False.

        Returns:
            string: Returns a string containing "Coordinates matched." if successful.
        """
        if self.verbose:
            print(f"Getting coordinates of {name} from CDS.")
        self.logger.info("Querying CDS for target coordinates.")
        c = SkyCoord.from_name(name)
        [apra, apdec] = skycoord_to_ap_radec(c)
        print(f"Slewing to {name} at position {apra} {apdec}")
        self.logger.info(f"Slewing to target {name}")
        result = self.slew(apra, apdec, wait=wait)
        return result

    def move(self, arcmin:float, direction:str="n", wait:bool=True):
        """Move the telescope by a specified number of arcminutes in a cardinal direction.

        Args:
            arcmin (float): Number of arcminutes to jog.
            direction (str, optional): One of "n", "s", "e", or "w". Defaults to "n".

        Raises:
            APMountError: _description_
        """
        pos1 = self.position()
        [rad, decd] = ap_radec_to_deg(pos1['ra'], pos1['dec'])
        if direction.lower() == "n":
            new_rad = rad
            new_decd = decd + arcmin/60.0
        elif direction.lower() == "s":
            new_rad = rad
            new_decd = decd - arcmin/60.0
        elif direction.lower() == "e":
            new_rad = rad + arcmin/60.0
            new_decd = decd
        elif direction.lower() == "w":
            new_rad = rad - arcmin/60.0
            new_decd = decd
        else:
            raise APMountError("Unknown direction.")
        [new_ra, new_dec] = deg_to_ap_radec(new_rad, new_decd)
        self.logger.info(f"Moving {arcmin} arcmin to the {direction}")
        self.slew(new_ra, new_dec, wait=wait)
        return "Jog complete."


    def movement_state(self):
        """Returns a string indicating whether the mount is stopped, tracking the stars, or slewing.

        Returns:
            string: One of: "stopped", "tracking at the sidereal rate", "slewing" or "unknown".
        """
        data1 = self.position()
        time.sleep(1)
        data2 = self.position()

        # If altitude and azimuth are the same, the mount must be stopped.
        if ((data1['altitude'] == data2['altitude']) and (data1['azimuth'] == data2['azimuth'])):
            self.status['is_slewing'] = False
            self.logger.info("Mount is stopped.")
            return "stopped"

        # If RA is the same the mount must be tracking at the sidereal rate.
        if (data1['ra'] == data2['ra']):
            self.status['is_slewing'] = False
            self.logger.info("Mount is tracking at the sidereal rate.")
            return "tracking at the sidereal rate"

        # If RA, altitude and azimuth are all different, the mount must be slewing.
        if ((data1['ra'] != data2['ra']) and
            (data1['altitude'] != data2['altitude']) and
                (data1['azimuth'] != data2['azimuth'])):
            self.status['is_slewing'] = True
            self.logger.info("Mount is slewing.")
            return "slewing"

        # There are other other options, e.g. the lunar rate, King rate, custom rate, etc.,
        # but we won't check for these.
        self.logger.info("Movement state unknown.")
        return "unknown"


    def set_center_rate(self, rate: int = 1):
        """Sets the centering rate for pulse moves.

        Args:
            rate (int, optional): One of 0 (12x), 1 (64x), 2 (600x), 3 (1200x).
        """
        if rate < 0 or rate > 3:
            raise APMountError("Unknown centering rate")
        with self._activity_lock:
            self.send(f"#:RC{int(rate)}#", response_type=None)
        self.logger.info(f"Centering rate set to {rate}")


    def jog(self, direction: str = 'n', duration: float = 0.2):
        """Jog the telescope at the centering rate for a specified number of seconds.

        Args:
            direction (str, optional): One of "n", "s", "e", or "w". Defaults to "n".
            duration (float, optional): Number of seconds to pulse. Defaults to 0.2.
        """
        with self._activity_lock:
            self.send(f"#:M{direction.lower()}#", response_type=None)
            time.sleep(0.2)
            self.send(f"#:Q{direction.lower()}#", response_type=None)
        self.status['is_slewing'] = False
        self.logger.info(f"Jogged {direction} for {duration} seconds.")
        return "Mount pulsed."


    def park(self):
        """Parks the mount at the current position.
        """
        with self._activity_lock:
            self.send("#:KA#", response_type=None)
        self.status['is_slewing'] = False
        self.logger.info("Mount parked.")
        return "Mount parked."


    def unpark(self):
        """Un-parks the mount.
        """
        with self._activity_lock:
            self.send("#:PO#", response_type=None)
        self.status['is_slewing'] = False
        self.logger.info("Mount un-parked.")
        return "Mount un-parked."


    def start(self):
        """Starts tracking.
        """
        with self._activity_lock:
            self.send("#:RT2#", response_type=None)
        self.status['is_slewing'] = False
        self.logger.info("Tracking started.")
        return "Tracking started."


    def stop(self):
        """Stops tracking.
        """
        with self._activity_lock:
            self.send("#:RT9#", response_type=None)
        self.status['is_slewing'] = False
        self.logger.info("Tracking stopped.")
        return "Tracking stopped."


    def panic(self):
        """Immediately halts all motion.
        """
        with self._activity_lock:
            self.send("#:Q#", response_type=None)
        self.status['is_slewing'] = False
        self.logger.info("Panic button pressed. All movement halted.")
        return "Panic button pressed. All movement halted"
    
    
def demo():
    print('Searching for mount.')
    serial_port = find_mount_serial_port()
    print(f'Mount found on port: {serial_port}')
    pp = pprint.PrettyPrinter(indent=2)
    print('Creating a GTOControlBox() object.')
    gto = GTOControlBox(serial_port, verbose=False)
    print('Connecting to the mount.')
    gto.connect()
    print('Setting mount date to today.')
    data = gto.set_date()
    print('Setting mount time to the current local time.')
    data = gto.set_local_time()
    print('Getting geographical and time information stored on the mount:')
    data = gto.location()
    pp.pprint(data)
    print('Getting pointing information from the mount:')
    data = gto.position()
    pp.pprint(data)
    print('Poll position every 5 seconds for 30 seconds (see log file for results)')
    gto._polling_interval = 5
    gto.start_polling()
    time.sleep(30)
    print('Stop polling.')
    gto.stop_polling()
    print('Disconnecting from the mount.')
    gto.disconnect()