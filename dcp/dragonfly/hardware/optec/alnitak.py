import serial
import time
import sys

from enum import Enum

from dragonfly.find import find_powerbox_serial_port
from dragonfly.log import DFLog

class FlipFlatInfo(Enum):
    # motor state
    NOT_RUNNING  = 0
    RUNNING      = 1
    # flap state
    FLAP_UNKNOWN = 2
    FLAP_CLOSED  = 3
    FLAP_OPEN    = 4
    FLAP_TIMEOUT = 5
    # light state
    LIGHT_OFF    = 6
    LIGHT_ON     = 7
    
class FlipFlatError(Exception):
    """Exception raised when an error occurs in an Alnitak FlipFlat lamp."

    Attributes:
        message - error message
    """

    def __init__(self, message:str = "FlipFlat error.", custom_field:str = '[FlipFlat]'):
        self. message = message
        self.logger = DFLog('FlipFlat').logger
            
        self.logger.error(self.message)
        super().__init__(self.message)
    pass

FLIPFLAP = 99
FLATMAN = 19
FLATMANXL = 10
FLATMANL = 15
FLATMASK = 18
# motor state
NOT_RUNNING = 0
RUNNING = 1
# flap state
FLAP_UNKNOWN = 0
FLAP_CLOSED = 1
FLAP_OPEN = 2
FLAP_TIMEOUT = 3
# light state
LIGHT_OFF = 0
LIGHT_ON = 1


class FlatMan(object):

    __serialPort = None
    __serialCon = None
    __data = None
    __str = ""
    __model = 0
    __stateFlipFlat = FLAP_UNKNOWN
    __debug = False
    __motorState = NOT_RUNNING
    __lightState = LIGHT_OFF
    
    # I found this class on the internet and modified it to have the same
    # conventions as my other software by using the following translation
    # layer.
    
    def connect(self):
        self.Connect()
        self.Ping()
        return "FlipFlat connected."
    
    def disconnect(self):
        return self.Disconnect()
    
    def open_cover(self):
        return self.Open()
    
    def close_cover(self):
        return self.Close()
    
    def lamp_on(self):
        return self.Light("ON")
    
    def lamp_off(self):
        return self.Light("OFF")
    
    def brightness(self, level):
        return self.Brightness(level)
    
    def get_state(self):
        return self.GetState()
    
    # Code below is from the original class

    def __init__(self, serial_port, debug=False):
        if serial_port:
            self.__serialPort = serial_port
        self.__debug = debug

    def Connect(self):
        try:
            self.__serialCon = serial.Serial(
                self.__serialPort, 9600, timeout=0, rtscts=False, dsrdtr=False
            )
        except Exception as e:
            if self.__debug:
                print("connection error : {0}".format(e))
            return False
        # Magic dance
        self.__serialCon.dtr = True
        self.__serialCon.rts = True

        self.__serialCon.dtr = True
        self.__serialCon.rts = False
        time.sleep(1.1)

        self.__serialCon.dtr = False
        self.__serialCon.rts = False
        time.sleep(1.1)

        # self.__serialCon.nonblocking()
        if self.__debug:
            print("Connection opened")
        return True

    def Disconnect(self):
        self.__serialCon.close()
        self.__serialCon = None

    def ReadData(self):
        s = self.__serialCon.read(1)
        s = s.decode()
        if len(s) and s.find("\n") != -1:
            self.__str += s
            tmp = self.__str.split("\n")
            self.__data = tmp[0]
            self.__str = ""
        else:
            self.__str += s
            time.sleep(0.001)
        if self.__debug:
            if self.__data:
                print("[ReadData] data from device : %s" % self.__data)

    def Ping(self):
        self.__data = None
        self.__serialCon.write(str.encode(">P000\n"))
        timeout = time.time() + 2
        while True:
            self.ReadData()
            if self.__data and self.__data.startswith("*P"):
                # extract model
                self.__model = int(self.__data[2:4])
                if self.__debug:
                    print("Model = %d\n" % self.__model)
                break
            now = time.time()
            if now > timeout:
                if self.__debug:
                    print("[Ping] Timeout waiting for response")
                return False
        return True

    def Open(self):
        self.__data = None
        if self.__model != FLIPFLAP and self.__model != FLATMASK:
            print("Model is not a Flip-Flat : %d\n" % self.__model)
            return False
        self.__serialCon.write(str.encode(">O000\n"))
        timeout = time.time() + 60
        while True:
            self.ReadData()
            if self.__data and self.__data.startswith("*O"):
                break
            now = time.time()
            if now > timeout:
                if self.__debug:
                    print("[Open] Timeout waiting for response")
                return False
        # wait for pannel to fully open
        timeout = time.time() + 60
        if self.__debug:
            print("[Open]  Waiting for flap to fully open")

        while True:
            if self.__debug:
                if sys.version_info[0] < 3:
                    print("."),
                else:
                    print(".", end="")
            self.GetState()
            if self.__stateFlipFlat == FLAP_OPEN:
                break
            now = time.time()
            if now > timeout:
                if self.__debug:
                    print("[Open] Timeout waiting for response")
            time.sleep(1)
        return True

    def Close(self):
        self.__data = None
        if self.__model != FLIPFLAP and self.__model != FLATMASK:
            print("Model is not a Flip-Flat : %d\n" % self.__model)
            return FALSE
        self.__serialCon.write(str.encode(">C000\n"))
        timeout = time.time() + 60
        while True:
            if self.__debug:
                print(
                    ".",
                )
            self.ReadData()
            if self.__data and self.__data.startswith("*C"):
                break
            now = time.time()
            if now > timeout:
                if self.__debug:
                    print("[Close] Timeout waiting for response")
                return False
        # wait for pannel to fully close
        timeout = time.time() + 60
        if self.__debug:
            print("[Close]  Waiting for flap to fully closed")
        while True:
            self.GetState()
            if self.__stateFlipFlat == FLAP_CLOSED:
                break
            now = time.time()
            if now > timeout:
                if self.__debug:
                    print("[Open] Timeout waiting for response")
            time.sleep(1)
        return True

    def GetState(self):
        self.__data = None
        self.__serialCon.write(str.encode(">S000\n"))
        timeout = time.time() + 60
        while True:
            self.ReadData()
            if self.__data and self.__data.startswith("*S"):
                break
            now = time.time()
            if now > timeout:
                if self.__debug:
                    print("[GetState] Timeout waiting for response")
                return False
        try:
            if self.__debug:
                print("self.__data = %s" % self.__data)
            self.__motorState = int(self.__data[4])
            self.__lightState = int(self.__data[5])
            self.__stateFlipFlat = int(self.__data[6])
            if self.__debug:
                print("self.__motorState = %d" % self.__motorState)
                print("self.__lightState = %d" % self.__lightState)
                print("self.__stateFlipFlat = %d" % self.__stateFlipFlat)

        except Exception as e:
            print("[GetState] Invalid response")
            print(e)
            return

    def Light(self, state):
        self.__data = None
        # FlipFlat need to be closed before we can switch the light on.
        if (
            self.__model == FLIPFLAP or self.__model == FLATMASK
        ) and self.__stateFlipFlat != FLAP_CLOSED:
            if not self.Close():
                return FALSE
        if state == "ON":
            self.__serialCon.write(str.encode(">L000\n"))
        else:
            self.__serialCon.write(str.encode(">D000\n"))

        timeout = time.time() + 2
        while True:
            self.ReadData()
            if self.__data and (
                self.__data.startswith("*L") or self.__data.startswith("*D")
            ):
                break
            now = time.time()
            if now > timeout:
                if self.__debug:
                    print("[Light] Timeout waiting for response")
                return False
        return True

    def Brightness(self, level):
        self.__data = None
        if level > 255:
            level = 255
        if level < 0:
            level = 0
        self.__serialCon.write(str.encode(">B%03d\n" % level))
        timeout = time.time() + 2
        while True:
            self.ReadData()
            if self.__data and self.__data.startswith("*B"):
                break
            now = time.time()
            if now > timeout:
                if self.__debug:
                    print("[Brightness] Timeout waiting for response")
                return False
        return True

    def Status(self):
        self.__data = None
        self.__serialCon.write(str.encode(">S000\n"))

        self.GetState()

        print("self.__motorState = %d" % self.__motorState)
        print("self.__lightState = %d" % self.__lightState)
        print("self.__stateFlipFlat = %d" % self.__stateFlipFlat)

        return True
