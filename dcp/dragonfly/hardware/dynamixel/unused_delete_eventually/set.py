# This script sets the motor to a given angle
# example to set the motor to 5 degrees: python set.py 5
import time
import json
import os
from dynamixel_sdk import *                    # Uses Dynamixel SDK library
from ctrl_table_settings import *              # Control table addresses and settings variables stored in here  (including bits and DEVICENAME)


#get the saved zeropoint angle
f = open(os.path.join(DYNAMIXEL_PATH, FN_MOTORSETTINGS))
motor = json.load(f)
zeropoint_angle = motor['zeropoint_angle']
f.close()

#get the angle we want to move to
if len(sys.argv) != 2:
    print("Need to input an angle to tilt to. Example: python set.py 5")
    exit()
dxl_goal_angle = float(sys.argv[1]) 
raw_dxl_goal_angle = (float(sys.argv[1]) + zeropoint_angle)
dxl_goal_position = int(round((dxl_goal_angle + zeropoint_angle)*(bits/360)))

#check it is within range
if (dxl_goal_position>DXL_MAXIMUM_POSITION_VALUE) or (dxl_goal_position<DXL_MINIMUM_POSITION_VALUE ):
    print("Error. Angle outside of range")
    quit()

# Initialize PortHandler instance
# Set the port path
# Get methods and members of PortHandlerLinux or PortHandlerWindows
portHandler = PortHandler(DEVICENAME)

# Initialize PacketHandler instance
# Set the protocol version
# Get methods and members of Protocol1PacketHandler or Protocol2PacketHandler
packetHandler = PacketHandler(PROTOCOL_VERSION)

# Open port
if portHandler.openPort():
    a=1 #useless filler line of code
    # print("Succeeded to open the Dynamixel port")
else:
    print("Error: Failed to open the Dynamixel port")
    quit()

# Set port baudrate
if portHandler.setBaudRate(BAUDRATE):
    a=1 #useless filler line of code
    # print("Succeeded to change the Dynamixel baudrate")
else:
    print("Error: Failed to change the Dynamixel baudrate")
    quit()

##### below is the equivalent to "initmotor.py" Seery will overhaul this soon so it is less clunky###

#Functions
def safe_write2ByteTxRx( ADDR, VAR):
    """Sends the packetHandler.write2ByteTxRx command, checks there is no error, prints it if there is.
    ADDR = control table address
    VAR = the value being set"""
    dxl_comm_result, dxl_error = packetHandler.write2ByteTxRx(portHandler, DXL_ID, ADDR, VAR)
    if dxl_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
    elif dxl_error != 0:
        print("%s" % packetHandler.getRxPacketError(dxl_error))

def safe_write4ByteTxRx( ADDR, VAR):
    """Sends the packetHandler.write4ByteTxRx command, checks there is no error, prints it if there is.
    ADDR = control table address
    VAR = the value being set"""
    dxl_comm_result, dxl_error = packetHandler.write4ByteTxRx(portHandler, DXL_ID, ADDR, VAR)
    if dxl_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
    elif dxl_error != 0:
        print("%s" % packetHandler.getRxPacketError(dxl_error))

# Disable Dynamixel Torque so we can change the PID gains and profiles
dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, DXL_ID, ADDR_PRO_TORQUE_ENABLE, TORQUE_DISABLE)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))

# Set the PID gains
safe_write2ByteTxRx( ADDR_PRO_POSITION_P_GAIN, POSITION_P_GAIN)
safe_write2ByteTxRx( ADDR_PRO_POSITION_I_GAIN, POSITION_I_GAIN)
safe_write2ByteTxRx( ADDR_PRO_POSITION_D_GAIN, POSITION_D_GAIN)

#Set the profile velocity and acceleration
safe_write4ByteTxRx( ADDR_PRO_PROFILE_VELOCITY, PROFILE_VELOCITY)
safe_write4ByteTxRx( ADDR_PRO_PROFILE_ACCELERATION, PROFILE_ACCELERATION)

#Set max/min position limits
safe_write4ByteTxRx( ADDR_PRO_MAX_POSITION_LIMIT, DXL_MAXIMUM_POSITION_VALUE)
safe_write4ByteTxRx( ADDR_PRO_MIN_POSITION_LIMIT, DXL_MINIMUM_POSITION_VALUE)

#######################################################################################

# Enable Dynamixel Torque
dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, DXL_ID, ADDR_PRO_TORQUE_ENABLE, TORQUE_ENABLE)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))
else:
    a=1 #useless filler line of code
    # print("Dynamixel has been successfully connected")

# Write goal position
dxl_comm_result, dxl_error = packetHandler.write4ByteTxRx(portHandler, DXL_ID, ADDR_PRO_GOAL_POSITION, dxl_goal_position)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))

# Delays for 2 seconds so filter tilter can move
time.sleep(2)  

# Read present position
dxl_present_position, dxl_comm_result, dxl_error = packetHandler.read4ByteTxRx(portHandler, DXL_ID, ADDR_PRO_PRESENT_POSITION)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))

#output print
print("A= %.2f,OK"%(360*dxl_present_position/bits - zeropoint_angle))
# print("     goal_step:%03d  step:%03d" % (dxl_goal_position, dxl_present_position))
# print("     goal_angle:%.2f  angle:%.2f" % (dxl_goal_angle, (360*dxl_present_position/bits - zeropoint_angle)))

#save the current step and angle in the json file
motor["step"] = dxl_present_position
motor["angle"] = (360*dxl_present_position/bits - zeropoint_angle)
motor['raw_angle'] = 360*dxl_present_position/bits
with open(os.path.join(DYNAMIXEL_PATH, FN_MOTORSETTINGS), 'w') as file:
    json.dump(motor, file)
file.close()

# Close port
portHandler.closePort()
