#!/usr/bin/env python
# -*- coding: utf-8 -*-

#import os
#import sys

#sys.path.insert(0,"C:/Users/seery/Documents/Dynamixel/DynamixelSDK/python/src" )
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

# Open port
if portHandler.openPort():
    print("Succeeded to open the port")
else:
    print("Failed to open the port")
    quit()

# Set port baudrate
if portHandler.setBaudRate(BAUDRATE):
    print("Succeeded to change the baudrate")
else:
    print("Failed to change the baudrate")
    quit()

# Disable Dynamixel Torque
dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, DXL_ID, ADDR_PRO_TORQUE_ENABLE, TORQUE_DISABLE)
if dxl_comm_result == COMM_SUCCESS:
    print('Succesfully disabled torque')
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
    print('Unsuccesfully disabled torque')
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))
    

# Close port
portHandler.closePort()
