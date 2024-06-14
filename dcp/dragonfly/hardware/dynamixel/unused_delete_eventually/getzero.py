# This script prints the zeropoint angle
import json
import os
from ctrl_table_settings import *              # Control table addresses and settings variables stored in here (including bits and DEVICENAME)

#get the saved zeropoint angle
f = open(os.path.join(DYNAMIXEL_PATH, FN_MOTORSETTINGS))
motor = json.load(f)
f.close()

#output print
print("Z= %.2f,OK"%(motor['zeropoint_angle']))
#print("zeropoint_step:%03d,  zeropoint_angle:%.2f" % ( motor['zeropoint_step'], motor['zeropoint_angle']))
