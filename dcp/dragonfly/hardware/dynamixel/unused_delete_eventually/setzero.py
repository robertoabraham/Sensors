# This script sets a given raw angle as the new zeropoint
# example: python setzero.py 180
# does NOT check with the dynamxiel current angle, it updates the zeropoints and angles of the json file based on the stored values
import json
import os
from dynamixel_sdk import *                    # Uses Dynamixel SDK library
from ctrl_table_settings import *              # Control table addresses and settings variables stored in here

#get the current saved zeropoint angle
f = open(os.path.join(DYNAMIXEL_PATH, FN_MOTORSETTINGS))
motor = json.load(f)
zeropoint_angle = motor['zeropoint_angle']
f.close()

#check we are getting a number to set zero to
if len(sys.argv) != 2:
    print("Need to input an angle to tilt to. Example: python setzero.py 180")
    exit()

new_zeropoint_angle = float(sys.argv[1]) 
new_zeropoint_step = int(float(sys.argv[1])*bits/360.)
motor['zeropoint_step'] = new_zeropoint_step
motor['zeropoint_angle'] = new_zeropoint_angle
motor['angle'] = motor['angle'] + zeropoint_angle - new_zeropoint_angle

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
# print("zeropoint_step:%03d,  zeropoint_angle:%.2f" %( motor['zeropoint_step'], motor['zeropoint_angle']))
