#ENTIRELY UNTESTED - SC/05-20-2022
import time
import json
import os
import argparse
import sys
from dragonfly.hardware.dynamixel.dynamixel_sdk import *                    # Uses Dynamixel SDK library
from dragonfly.hardware.dynamixel.ctrl_table_settings import *              # Control table addresses and settings variables stored in here (including bits and DEVICENAME)

############################## Variables #######################################################################
# Path to this directory
# DYNAMIXEL_PATH = "C:\\Users\seery\df\Dragonfly-MaximDL\Python\Dynamixel\\"  #on Seery's local machine
# DYNAMIXEL_PATH = "C:\\Users\Dragonfly\Documents\Git\Dragonfly-MaximDL\Python\Dynamixel\\"   #on the sticks
# DYNAMIXEL_PATH = "/server/executables/Dynamixel/" #on the raspberry pis in docker
# DYNAMIXEL_PATH = "/data/" #new, moving the motorsettings json to a state file
DYNAMIXEL_PATH = "/home/dragonfly/dragonfly-arm/active_optics/dcp/dragonfly/hardware/dynamixel/"
# FN_MOTORSETTINGS = "motorsettings.json" #adding motorsetting file into settings so easier to change
FN_MOTORSETTINGS = "state.txt" # putting FT motor info into state.txt so just one text file to read/write from

# Port
# DEVICENAME = 'COM6'    # on Seery's local machine
DEVICENAME = "/dev/ttyUSB0"  # on 30 lens array
# Check which port is being used on your controller
# ex) Windows: "COM1"   Linux: "/dev/ttyUSB0" Mac: "/dev/tty.usbserial-*"

# Other Useful variables
# gearing = 36./24. #filter shaft gear / motor gear
gearing = 1.0
bits = 4096 * gearing
settletime = 2

# Dynamixel control table address
ADDR_PRO_TORQUE_ENABLE = 64  # Control table address is different in Dynamixel model
ADDR_PRO_GOAL_POSITION = 116
ADDR_PRO_PRESENT_POSITION = 132
ADDR_PRO_POSITION_P_GAIN = 84
ADDR_PRO_POSITION_I_GAIN = 82
ADDR_PRO_POSITION_D_GAIN = 80
ADDR_PRO_PROFILE_VELOCITY = 112
ADDR_PRO_PROFILE_ACCELERATION = 108
ADDR_PRO_MAX_POSITION_LIMIT = 48
ADDR_PRO_MIN_POSITION_LIMIT = 52

# Protocol version
PROTOCOL_VERSION = 2.0  # See which protocol version is used in the Dynamixel, 2.0 is default for our motors

# Default setting
DXL_ID = 1  # Dynamixel ID : 1
BAUDRATE = 57600  # Dynamixel default baudrate : 57600
TORQUE_ENABLE = 1  # Value for enabling the torque
TORQUE_DISABLE = 0  # Value for disabling the torque

#set hard limits to +/- 25 degrees from zero, note this does not change when you change 
#    the zeropoint of the motor
DXL_MINIMUM_POSITION_VALUE  = 1763           # Dynamixel will rotate between this value
DXL_MAXIMUM_POSITION_VALUE  = 2332           # and this value (note that the Dynamixel would not move when the position value is out of movable range.)
# DXL_MOVING_STATUS_THRESHOLD = 1               # Dynamixel moving status threshold (originally 20)

# Gain and profile settings
POSITION_P_GAIN = 2000
POSITION_I_GAIN = 2
POSITION_D_GAIN = 10
PROFILE_VELOCITY = 220
PROFILE_ACCELERATION = 25
##########################################################################################################################

class Dynamixel_Motor(object):
    __serialPort = None
    __serialCon = None
    __data = None
    __str = ""
    __portHandler = None
    __packetHandler = None
    zeropoint_angle = None
    zeropoint_step = None
    dxl_present_position = None
    dxl_goal_position = None
    dxl_goal_angle = None
    raw_dxl_goal_angle =None
    
    new_statefile = None

    def __init__(self, port=DEVICENAME, path=DYNAMIXEL_PATH, ms_fn=FN_MOTORSETTINGS):
        self.portHandler = PortHandler(port)
        self.packetHandler = PacketHandler(PROTOCOL_VERSION)
        self.path = path
        self.ms_fn = ms_fn
        
        # Check if the state file exists, and if not create it.
        if (not os.path.exists(os.path.join(path, ms_fn))):
            print("Creating state file %s" % os.path.join(path, ms_fn))
            f = open(os.path.join(path, ms_fn), "w")
            f.write('{"zeropoint_angle": 180.0, "zeropoint_step": 2076, "step": 2105, "angle": 0.0, "raw_angle": 180.0, "needs_refresh": true}')
            f.close()
            self.new_statefile = True
        else:
            self.new_statefile = False

        #get the saved zeropoint angle
        f = open(os.path.join(path, ms_fn))
        motorsettings = json.load(f)
        self.zeropoint_angle = motorsettings['zeropoint_angle']
        self.zeropoint_step = motorsettings['zeropoint_step']
        self.dxl_present_position = motorsettings['angle']
        f.close()

    ################################# Lower Level Commands #################################################
    def open_port(self):
        # Open port
        if self.portHandler.openPort():
            a=1 #useless filler line of code
            # print("Succeeded to open the Dynamixel port")
        else:
            print("Error: Failed to open the Dynamixel port")
            quit()

        # Set port baudrate
        if self.portHandler.setBaudRate(BAUDRATE):
            a=1 #useless filler line of code
            # print("Succeeded to change the Dynamixel baudrate")
        else:
            print("Error: Failed to change the Dynamixel baudrate")
            quit()
    
    def close_port(self):
        self.portHandler.closePort()
    
    def safe_write2ByteTxRx(self, ADDR, VAR):
        """Sends the packetHandler.write2ByteTxRx command, checks there is no error, prints it if there is.
        ADDR = control table address
        VAR = the value being set"""
        dxl_comm_result, dxl_error = self.packetHandler.write2ByteTxRx(self.portHandler, DXL_ID, ADDR, VAR)
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))

    def safe_write4ByteTxRx(self, ADDR, VAR):
        """Sends the packetHandler.write4ByteTxRx command, checks there is no error, prints it if there is.
        ADDR = control table address
        VAR = the value being set"""
        dxl_comm_result, dxl_error = self.packetHandler.write4ByteTxRx(self.portHandler, DXL_ID, ADDR, VAR)
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))

    def enable_torque(self):
        dxl_comm_result, dxl_error = self.packetHandler.write1ByteTxRx(self.portHandler, DXL_ID, ADDR_PRO_TORQUE_ENABLE, TORQUE_ENABLE)
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))
        else:
            a=1 #useless filler line of code
            # print("Dynamixel has been successfully connected")

    def disable_torque(self):
        dxl_comm_result, dxl_error = self.packetHandler.write1ByteTxRx(self.portHandler, DXL_ID, ADDR_PRO_TORQUE_ENABLE, TORQUE_DISABLE)
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))

    def save_info(self):
        f = open(os.path.join(self.path, self.ms_fn))
        motorsettings = json.load(f)
        f.close()
        #save the current step and angle in the json file
        motorsettings["step"] = self.dxl_present_position
        motorsettings["angle"] = (360*self.dxl_present_position/bits - self.zeropoint_angle)
        motorsettings['raw_angle'] = 360*self.dxl_present_position/bits
        with open(os.path.join(self.path, self.ms_fn), 'w') as file:
            json.dump(motorsettings, file)
        file.close()
    
    def check_goal_position(self):
        #check it is within range
        if (self.dxl_goal_position>DXL_MAXIMUM_POSITION_VALUE) or (self.dxl_goal_position<DXL_MINIMUM_POSITION_VALUE ):
            print("Error. Angle outside of range (dynamixel values)")
            quit()
        if (self.dxl_goal_angle>(20)) or (self.dxl_goal_angle<(-20)):
            print("Error. Angle outside of range (+/- 20 deg)")
            quit()

    def read_position(self):
        # Read present position
        self.open_port()
        self.dxl_present_position, dxl_comm_result, dxl_error = self.packetHandler.read4ByteTxRx(self.portHandler, DXL_ID, ADDR_PRO_PRESENT_POSITION)
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))
        self.close_port()

    def write_goal_position(self, waittime=settletime):
        # Write goal position
        self.open_port()
        self.enable_torque()
        dxl_comm_result, dxl_error = self.packetHandler.write4ByteTxRx(self.portHandler, DXL_ID, ADDR_PRO_GOAL_POSITION, self.dxl_goal_position)
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))
        self.close_port()
        # Delays for a given number of seconds so filter tilter can move
        time.sleep(waittime)

    
    ##################################### Higher Level Commands ##################################################
    def initmotor(self):
        """Initialize motors by setting PID gains, velocity profiles, and max/min limits"""
        self.open_port()
        self.disable_torque()
        # Set the PID gains
        self.safe_write2ByteTxRx( ADDR_PRO_POSITION_P_GAIN, POSITION_P_GAIN)
        self.safe_write2ByteTxRx( ADDR_PRO_POSITION_I_GAIN, POSITION_I_GAIN)
        self.safe_write2ByteTxRx( ADDR_PRO_POSITION_D_GAIN, POSITION_D_GAIN)

        #Set the profile velocity and acceleration
        self.safe_write4ByteTxRx( ADDR_PRO_PROFILE_VELOCITY, PROFILE_VELOCITY)
        self.safe_write4ByteTxRx( ADDR_PRO_PROFILE_ACCELERATION, PROFILE_ACCELERATION)

        #Set max/min position limits
        self.safe_write4ByteTxRx( ADDR_PRO_MAX_POSITION_LIMIT, DXL_MAXIMUM_POSITION_VALUE)
        self.safe_write4ByteTxRx( ADDR_PRO_MIN_POSITION_LIMIT, DXL_MINIMUM_POSITION_VALUE)
        self.close_port()


    def get(self):
        """Get the zeropoint adjusted angle"""
        self.open_port()
        self.read_position()
        str = "%.2f" % (360 * self.dxl_present_position / bits - self.zeropoint_angle)
        self.save_info()
        self.close_port()
        return float(str)

    def getraw(self):
        """Get the raw angle of the filter titler"""
        self.open_port()
        self.read_position()
        str = "%.2f" % (360 * self.dxl_present_position / bits)
        self.save_info()
        self.close_port()
        return float(str)
    
    def getzero(self):
        #get the saved zeropoint angle again
        f = open(os.path.join(self.path, self.ms_fn))
        motorsettings = json.load(f)
        self.zeropoint_angle = motorsettings['zeropoint_angle']
        f.close()
        str = "%.2f"%(self.zeropoint_angle)
        return float(str)
        
    def move(self, nsteps):
        """Moves the motor by nsteps"""
        self.read_position()
        self.dxl_goal_position = int(self.dxl_present_position + nsteps)
        self.dxl_goal_angle = self.dxl_goal_position*360./bits - self.zeropoint_angle
        self.check_goal_position()
        self.initmotor()
        self.write_goal_position() 
        self.read_position() 
        self.save_info()
    
    def set(self, angle):
        """Sets the motor to a given angle"""
        self.read_position()
        self.dxl_goal_angle = float(angle)
        self.raw_dxl_goal_angle = (float(angle) + self.zeropoint_angle)
        self.dxl_goal_position = int(round((self.dxl_goal_angle + self.zeropoint_angle)*(bits/360.)))
        self.check_goal_position()
        self.initmotor()
        self.write_goal_position()
        self.read_position()
        self.save_info()
    
    def setraw(self, rawangle):
        """sets the motor to a given raw angle"""
        self.read_position()
        self.dxl_goal_angle = (float(rawangle) - self.zeropoint_angle)
        self.raw_dxl_goal_angle = (float(rawangle))
        self.dxl_goal_position = int(round((self.raw_dxl_goal_angle )*(bits/360.)))
        self.check_goal_position()
        self.initmotor()
        self.write_goal_position()
        self.read_position()
        self.save_info()

    def setzero(self, zeropointangle):
        """Sets a given raw angle as the new zeropoint"""
        #get the current saved zeropoint angle
        f = open(os.path.join(self.path, self.ms_fn))
        motorsettings = json.load(f)
        zeropoint_angle = motorsettings['zeropoint_angle']
        f.close()
        #get the new angle
        new_zeropoint_angle = float(zeropointangle) 
        new_zeropoint_step = int(new_zeropoint_angle*bits/360.)
        motorsettings['zeropoint_step'] = new_zeropoint_step
        motorsettings['zeropoint_angle'] = new_zeropoint_angle
        motorsettings['angle'] = motorsettings['angle'] + zeropoint_angle - new_zeropoint_angle
        #check current position is a reasonable value for zeropoint
        if abs(new_zeropoint_angle - 180.) > 90.: 
            print('Angle is greater than 90 deg away 180 degrees. New zeropoint will not be set')
            exit()
        #save current position as zeropoint 
        with open(os.path.join(self.path, self.ms_fn), 'w') as file:
            json.dump(motorsettings, file)   
        file.close()
        #output print
        print("Z= %.2f,OK"%(motorsettings['zeropoint_angle']))

    def zero(self):
        """Sets the current raw angle as the new zeropoint"""
        self.read_position()
        new_zeropoint_angle = 360*self.dxl_present_position/bits
        self.setzero(new_zeropoint_angle)
##############################################################################################################


def usage():
    print(
        "dynamixel.py  --port=</dev/port> --init | --get, getraw, getzero, zero | --set, setraw, setzero =<angle in degrees> [--help]"
    )
    return


def main():
    parser = argparse.ArgumentParser(description="Control Dynamixel Motor")

    parser.add_argument(
        "--path",
        nargs="?",
        default=DYNAMIXEL_PATH,
        type=str,
        help="Path to the motorsettings json file (default %s)"%DYNAMIXEL_PATH,
    )
    parser.add_argument(
        "--filename",
        nargs="?",
        default=FN_MOTORSETTINGS,
        type=str,
        help="Name of the motorsettings json file (default %s)"%FN_MOTORSETTINGS,
    )
    parser.add_argument(
        "--port",
        nargs="?",
        default=DEVICENAME,
        type=str,
        help="serial port of the motor (default %s)"%DEVICENAME,
    )
    parser.add_argument(
        "command",
        metavar="command",
        type=str,
        nargs="?",
        help="command to send to motor, options: init, get, getraw, getzero, set <angle>, setraw <angle>, zero, setzero <angle>",
    )
    parser.add_argument(
        "angle",
        metavar="angle",
        type=float,
        nargs="?",
        help="angle (float) the command is settng to",
    )

    args = parser.parse_args()
    motor = Dynamixel_Motor(port=args.port,path=args.path)

    if args.command == "init":
        motor.initmotor()
    elif args.command == "get":
        out = motor.get()
        print(out)
    elif args.command == "getraw":
        out = motor.getraw()
        print(out)
    elif args.command == "getzero":
        out = motor.getzero()
        print(out)
    elif args.command == "set":
        motor.set(args.angle)
    elif args.command == "setraw":
        motor.setraw(args.angle)
    elif args.command == "zero":
        motor.zero()
    elif args.command == "setzero":
        motor.setzero(args.angle)
    else:
        print("Unidentified Command")
        usage()
    return 0


if __name__ == "__main__":
    sys.exit(main())

