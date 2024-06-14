export port="$1"
echo "Using serial port: $port"
sudo ./apmount_serial.py -p $port -b 9600 -s "#" -d 500
sudo ./apmount_serial.py -p $port -b 9600 -s "#:GR#" -d 500 -r
sudo ./apmount_serial.py -p $port -b 9600 -s "#:GD#" -d 500 -r
sudo ./apmount_serial.py -p $port -b 9600 -s "#:GA#" -d 500 -r
sudo ./apmount_serial.py -p $port -b 9600 -s "#:GZ#" -d 500 -r

# Note that if you want to read simple messages from the mount (the ones
# that end in 1 or 1, you need to use -g and not -r!)
