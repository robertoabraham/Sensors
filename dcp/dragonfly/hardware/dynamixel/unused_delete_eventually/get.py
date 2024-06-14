# This script gets the current angle of the motor
# using the zeropoint angle from the motorsettings.json file
import json
import os
from dynamixel_sdk import *  # Uses Dynamixel SDK library
from ctrl_table_settings import *  # Control table addresses and settings variables stored in here (including bits and DEVICENAME)

# get the saved zeropoint angle
f = open(os.path.join(DYNAMIXEL_PATH, FN_MOTORSETTINGS))
motor = json.load(f)
zeropoint_angle = motor["zeropoint_angle"]
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
    a = 1  # useless filler line of code
    # print("Succeeded to open the port")
else:
    print("Failed to open the port")
    quit()

# Set port baudrate
if portHandler.setBaudRate(BAUDRATE):
    a = 1  # useless filler line of code
    # print("Succeeded to change the baudrate")
else:
    print("Failed to change the baudrate")
    quit()

# Read present position
dxl_present_position, dxl_comm_result, dxl_error = packetHandler.read4ByteTxRx(
    portHandler, DXL_ID, ADDR_PRO_PRESENT_POSITION
)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))

# output print
print("A= %.2f,OK" % (360 * dxl_present_position / bits - zeropoint_angle))
# print("step:%03d,  angle:%.2f" % ( dxl_present_position, (360*dxl_present_position/bits - zeropoint_angle)))

# save the current step and angle in the json file
motor["step"] = dxl_present_position
motor["angle"] = 360 * dxl_present_position / bits - zeropoint_angle
motor["raw_angle"] = 360 * dxl_present_position / bits

with open(os.path.join(DYNAMIXEL_PATH, FN_MOTORSETTINGS), "w") as file:
    json.dump(motor, file)
file.close()

# Close port
portHandler.closePort()
