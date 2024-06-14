# Path to this directory
# DYNAMIXEL_PATH = "C:\\Users\seery\df\Dragonfly-MaximDL\Python\Dynamixel\\"  #on Seery's local machine
# DYNAMIXEL_PATH = "C:\\Users\Dragonfly\Documents\Git\Dragonfly-MaximDL\Python\Dynamixel\\"   #on the sticks
# DYNAMIXEL_PATH = "/server/executables/Dynamixel/" #on the raspberry pis in docker


#new, moving the motorsettings json to outside of the git repo tracking
# so the settings are remembered
DYNAMIXEL_PATH = "/data/" #new, moving the motorsettings json to a state file
# FN_MOTORSETTINGS = "motorsettings.json" #adding motorsetting file into settings so easier to change
FN_MOTORSETTINGS = "state.txt" # putting FT motor info into state.txt so just one text file to read/write from

# Other Useful variables
# gearing = 36./24. #filter shaft gear / motor gear
gearing = 1.0
bits = 4096 * gearing

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
PROTOCOL_VERSION = 2.0  # See which protocol version is used in the Dynamixel

# Default setting
DXL_ID = 1  # Dynamixel ID : 1
BAUDRATE = 57600  # Dynamixel default baudrate : 57600
#DEVICENAME                  = 'COM5'    # on Seery's local machine
DEVICENAME = "/dev/ttyUSB0"  # on 30 lens array
# Check which port is being used on your controller
# ex) Windows: "COM1"   Linux: "/dev/ttyUSB0" Mac: "/dev/tty.usbserial-*"

TORQUE_ENABLE = 1  # Value for enabling the torque
TORQUE_DISABLE = 0  # Value for disabling the torque
#set hard limits to +/- 25 degrees from zero, note this does not change when you change 
#    the zeropoint of the motor
DXL_MINIMUM_POSITION_VALUE  = 0           # Dynamixel will rotate between this value
DXL_MAXIMUM_POSITION_VALUE  = 4093 
# DXL_MINIMUM_POSITION_VALUE  = 1763           # Dynamixel will rotate between this value
# DXL_MAXIMUM_POSITION_VALUE  = 2332           # and this value (note that the Dynamixel would not move when the position value is out of movable range. Check e-manual about the range of the Dynamixel you use.)
#DXL_MINIMUM_POSITION_VALUE = 2344  # These two values are centered +/- 30 deg from the position of the motor after NMS installed it on 301 in Nov 2021
#DXL_MAXIMUM_POSITION_VALUE = 3026  #
# DXL_MOVING_STATUS_THRESHOLD = 1               # Dynamixel moving status threshold (originally 20)

# Gain and profile settings
POSITION_P_GAIN = 2000
POSITION_I_GAIN = 2
POSITION_D_GAIN = 10
PROFILE_VELOCITY = 220
PROFILE_ACCELERATION = 25
