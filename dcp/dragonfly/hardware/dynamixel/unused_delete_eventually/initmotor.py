# Initializes the motor by setting the correct PID gains, profiles acceleration and velocity, 
# and enables torque

from dynamixel_sdk import *                    # Uses Dynamixel SDK library
from ctrl_table_settings import *              # Control table addresses and settings variables stored in here


# Initialize PortHandler instance
# Set the port path
# Get methods and members of PortHandlerLinux or PortHandlerWindows
portHandler = PortHandler(DEVICENAME)

# Initialize PacketHandler instance
# Set the protocol version
# Get methods and members of Protocol1PacketHandler or Protocol2PacketHandler
packetHandler = PacketHandler(PROTOCOL_VERSION)

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

# Open port
if portHandler.openPort():
    print("Succeeded to open the Dynamixel port")
else:
    print("Error: Failed to open the Dynamixel port")
    quit()


# Set port baudrate
if portHandler.setBaudRate(BAUDRATE):
    print("Succeeded to change the Dynamixel baudrate")
else:
    print("Error: Failed to change the Dynamixel baudrate")
    quit()

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

# Enable Dynamixel Torque
dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, DXL_ID, ADDR_PRO_TORQUE_ENABLE, TORQUE_ENABLE)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))
else:
    print("Dynamixel has been successfully enabled torque")

# Close port
portHandler.closePort()
