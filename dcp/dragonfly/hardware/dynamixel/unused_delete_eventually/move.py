# This script moves the motor a given number of steps
# example to set the motor to 5 degrees: python move.py 10
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

# Enable Dynamixel Torque
dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, DXL_ID, ADDR_PRO_TORQUE_ENABLE, TORQUE_ENABLE)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))
else:
    a=1 #useless filler line of code
    # print("Dynamixel has been successfully connected")

# Read present position
dxl_present_position, dxl_comm_result, dxl_error = packetHandler.read4ByteTxRx(portHandler, DXL_ID, ADDR_PRO_PRESENT_POSITION)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))

# Close port
portHandler.closePort()

#get the angle we want to move to
if len(sys.argv) != 2:
    print("Need to input an angle to tilt to. Example: python move.py 5")
    exit()
# if type(sys.argv[1] )!= int:
#     print("Number of steps needs to be an integer")
#     exit()
nsteps = int(sys.argv[1]) 
dxl_goal_position = dxl_present_position + nsteps
dxl_goal_angle = dxl_goal_position*360./bits - zeropoint_angle

#check it is within range
if (dxl_goal_position>DXL_MAXIMUM_POSITION_VALUE) or (dxl_goal_position<DXL_MINIMUM_POSITION_VALUE ):
    print("Error. Angle outside of range (dynamixel values)")
    quit()

if (dxl_goal_angle>(20)) or (dxl_goal_position<(-20)):
    print("Error. Angle outside of range (+/- 20 deg)")
    quit()

# Open port
if portHandler.openPort():
    a=1 #useless filler line of code
    # print("Succeeded to open the Dynamixel port")
else:
    print("Error: Failed to open the Dynamixel port")
    quit()

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
print("R= %.2f,OK"%(360*dxl_present_position/bits))
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
