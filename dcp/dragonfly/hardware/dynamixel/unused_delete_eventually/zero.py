# This script sets the zeropoint of the motor as the current angle
import json
import os
from dynamixel_sdk import *                    # Uses Dynamixel SDK library
from ctrl_table_settings import *              # Control table addresses and settings variables stored in here (including bits and DEVICENAME)

#get the current saved zeropoint angle
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
    # print("Succeeded to open the port")
else:
    print("Failed to open the port")
    quit()

# Set port baudrate
if portHandler.setBaudRate(BAUDRATE):
    a=1 #useless filler line of code
    # print("Succeeded to change the baudrate")
else:
    print("Failed to change the baudrate")
    quit()

# Read present position
dxl_present_position, dxl_comm_result, dxl_error = packetHandler.read4ByteTxRx(portHandler, DXL_ID, ADDR_PRO_PRESENT_POSITION)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))

#calculate new zeropoint angle and step position
new_zeropoint_step = dxl_present_position
new_zeropoint_angle = 360*dxl_present_position/bits
motor['zeropoint_step'] = new_zeropoint_step
motor['zeropoint_angle'] = new_zeropoint_angle
motor['angle'] = 0.0

#check current position is a reasonable value for zeropoint, normally would be >15 deg not >90 deg, but motor on 301 installed "crooked"
if abs(new_zeropoint_angle - 180.) > 90.: 
    print('Current angle is greater than 90 deg away 180 degrees. New zeropoint will not be set')
    exit()

#save current position as zeropoint 
with open(os.path.join(DYNAMIXEL_PATH, FN_MOTORSETTINGS), 'w') as file:
    json.dump(motor, file)   
file.close()

#output print
print("Z= %.2f,OK"%(motor['zeropoint_angle']))
# print("zeropoint_step:%03d,  zeropoint_angle:%.2f" % ( motor['zeropoint_step'], motor['zeropoint_angle']))

# Close port
portHandler.closePort()