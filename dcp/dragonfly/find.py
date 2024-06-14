import subprocess
import logging
import re
import ast
from datetime import datetime


# Set up logging.
logfile = '/tmp/dragonfly_log.txt'

fh = logging.FileHandler(logfile)
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
fh.setFormatter(formatter)
log = logging.getLogger('Finder')

# Add the handler to the logger if it doesn't already exist
if not any(isinstance(handler, logging.FileHandler) and handler.baseFilename == '/tmp/dragonfly_log.txt' for handler in log.handlers):
    log.addHandler(fh)
    
log.setLevel(logging.DEBUG)


def find_powerbox_serial_port():

    # Here is an example showing how you would figure out the USB path of the Powerbox:
    #
    # $ dmesg | grep "Pegasus Astro"
    # [    3.006057] usb 1-1.1.1: Manufacturer: Pegasus Astro
    #
    # So the device's USB path is "usb 1-1.1.1". To get the corresponding
    # serial port, look for the serial port name associated with that USB path:
    # 
    # $ dmesg | grep FTDI
    # ...
    # [    8.510003] usbserial: USB Serial support registered for FTDI USB Serial Device
    # [    8.510305] ftdi_sio 1-1.1.1:1.0: FTDI USB Serial Device converter detected
    # [    8.521264] usb 1-1.1.1: FTDI USB Serial Device converter now attached to ttyUSB0
    # [803007.201665] ftdi_sio 1-1.2:1.0: FTDI USB Serial Device converter detected
    # [803007.206790] usb 1-1.2: FTDI USB Serial Device converter now attached to ttyUSB2
    # ...
    #
    # In the example above, you can see that the "usb 1-1.1.1" is associated with ttyUSB0.
    # Thus the serial device is /dev/ttyUSB0.
    #
    # So you can see that we need a two-step process to isolate the correct device. 
    #
    # Step 1. Look for the the device name in dmesg and figure out the USB device path.
    # Step 2. Use the USB device path to find the port name.   
    #    
    # From the shell, this would be implemented as follows:
    #
    # usb=`dmesg | grep "Flat Fielder" | sed -n "s/^.*usb\s*\(\S*\):.*$/\1/p"`
    # dmesg | grep "USB Serial Device converter now attached" | grep $usb
    #
    # What follows is the Python equivalent.

    try:
        dmesg = subprocess.Popen(('dmesg'), stdout=subprocess.PIPE)
        grep1 = subprocess.Popen(('grep', 'Pegasus Astro'), stdin=dmesg.stdout, stdout=subprocess.PIPE)
        sed1 = subprocess.Popen(('sed', '-n', r"s/^.*usb\s*\(\S*\):.*$/\1/p"), 
                                stdin=grep1.stdout, stdout=subprocess.PIPE)
        serial_path = sed1.communicate()[0].decode().strip().split()[0]

        dmesg = subprocess.Popen(('dmesg'), stdout=subprocess.PIPE)
        grep1 = subprocess.Popen(('grep', 'USB Serial Device converter now attached'), 
                                stdin=dmesg.stdout, stdout=subprocess.PIPE)
        grep2 = subprocess.Popen(('grep', serial_path), stdin=grep1.stdout, stdout=subprocess.PIPE)
        port = grep2.communicate()[0].decode().strip().split()[-1]
        port = f"/dev/{port}"
        return port
    except subprocess.CalledProcessError:
        print("Powerbox not found.")
        

def find_filtertilter_serial_port():

    try:
        dmesg = subprocess.Popen(('dmesg'), stdout=subprocess.PIPE)
        grep1 = subprocess.Popen(('grep', 'Manufacturer: FTDI'), stdin=dmesg.stdout, stdout=subprocess.PIPE)
        sed1 = subprocess.Popen(('sed', '-n', r"s/^.*usb\s*\(\S*\):.*$/\1/p"), 
                                stdin=grep1.stdout, stdout=subprocess.PIPE)
        serial_path = sed1.communicate()[0].decode().strip().split()[0]

        dmesg = subprocess.Popen(('dmesg'), stdout=subprocess.PIPE)
        grep1 = subprocess.Popen(('grep', 'USB Serial Device converter now attached'), 
                                stdin=dmesg.stdout, stdout=subprocess.PIPE)
        grep2 = subprocess.Popen(('grep', serial_path), stdin=grep1.stdout, stdout=subprocess.PIPE)
        port = grep2.communicate()[0].decode().strip().split()[-1]
        port = f"/dev/{port}"
        return port
    except subprocess.CalledProcessError:
        print("Filter Tilter not found.")


def find_flipflat_serial_port():

    # Here is an example showing how you would figure out the USB path of the FlipFlat:
    #
    # $ dmesg | grep "Flat Fielder"
    # [803007.193724] usb 1-1.2: Product: Flat Fielder
    #
    # Now we can see the USB path is "usb 1-2.2". To get the corresponding
    # serial port, look for the serial port name associated with that USB path:
    # 
    # $ dmesg | grep FTDI
    # ...
    # [    8.510003] usbserial: USB Serial support registered for FTDI USB Serial Device
    # [    8.510305] ftdi_sio 1-1.1.1:1.0: FTDI USB Serial Device converter detected
    # [    8.521264] usb 1-1.1.1: FTDI USB Serial Device converter now attached to ttyUSB0
    # [803007.201665] ftdi_sio 1-1.2:1.0: FTDI USB Serial Device converter detected
    # [803007.206790] usb 1-1.2: FTDI USB Serial Device converter now attached to ttyUSB2
    # ...
    #
    # In the example above, you can see that the "usb 1-1.2" is associated with ttyUSB2.
    # Thus the serial device is /dev/ttyUSB2.
    #
    # So you can see that we need a two-step process to isolate the correct device. 
    #
    # Step 1. Look for the the device name in dmesg and figure out the USB device path.
    # Step 2. Use the USB device path to find the port name.   
    #    
    # From the shell, this would be implemented as follows:
    #
    # usb=`dmesg | grep "Flat Fielder" | sed -n "s/^.*usb\s*\(\S*\):.*$/\1/p"`
    # dmesg | grep "USB Serial Device converter now attached" | grep $usb
    #
    # What follows is the Python equivalent to the above.

    try:
        dmesg = subprocess.Popen(('dmesg'), stdout=subprocess.PIPE)
        grep1 = subprocess.Popen(('grep', 'Flat Fielder'), stdin=dmesg.stdout, stdout=subprocess.PIPE)
        sed1 = subprocess.Popen(('sed', '-n', r"s/^.*usb\s*\(\S*\):.*$/\1/p"), 
                                stdin=grep1.stdout, stdout=subprocess.PIPE)
        serial_path = sed1.communicate()[0].decode().strip().split()[0]

        dmesg = subprocess.Popen(('dmesg'), stdout=subprocess.PIPE)
        grep1 = subprocess.Popen(('grep', 'USB Serial Device converter now attached'), 
                                stdin=dmesg.stdout, stdout=subprocess.PIPE)
        grep2 = subprocess.Popen(('grep', serial_path), stdin=grep1.stdout, stdout=subprocess.PIPE)
        port = grep2.communicate()[0].decode().strip().split()[-1]
        port = f"/dev/{port}"
        return port
    except subprocess.CalledProcessError:
        print("Powerbox not found.")


def find_mount_serial_port():

    # This is the command line to find the mount USB serial port.
    # grep_line = "dmesg | grep pl2303 | tail -1 | grep tty"

    # Here is the Python equivalent.
    try:
        dmesg = subprocess.Popen(('dmesg'), stdout=subprocess.PIPE)
        grep1 = subprocess.Popen(('grep', 'pl2303'), stdin=dmesg.stdout, stdout=subprocess.PIPE)
        tail = subprocess.Popen(('tail', '-1'), stdin=grep1.stdout, stdout=subprocess.PIPE)
        grep2 = subprocess.Popen(('grep', 'tty'), stdin=tail.stdout, stdout=subprocess.PIPE)
        output = grep2.communicate()[0].decode().strip().split()
        # The USB serial port name is the last item in the list.
        port = f"/dev/{output[-1]}"
        log.info(f"Mount found on serial port: {port}")
        return port
    except subprocess.CalledProcessError:
        print("Mount not found.")


def seconds_since_info_refresh(logline: str):
    logentry_time = ' '.join([word.replace(',', '.') for word in logline.split()[0:2]])
    # Determine how many seconds since the message was sent
    format_string = "%Y-%m-%d %H:%M:%S.%f"
    logentry_datetime = datetime.strptime(logentry_time, format_string)
    seconds_since_info_refresh = (datetime.now() - logentry_datetime).seconds
    return seconds_since_info_refresh


def find_mount_info_in_log():
    grep = subprocess.Popen(('grep', 'AstroPhysics - {', logfile), stdout=subprocess.PIPE)
    tail = subprocess.Popen(('tail', '-1'), stdin=grep.stdout, stdout=subprocess.PIPE)
    output = tail.communicate()[0].decode().strip()
    result = ast.literal_eval(re.sub(r'^.*?{', '{', output))
    result['information_age_s'] = seconds_since_info_refresh(output)
    if result['information_age_s'] < 30:
        result['information_fresh'] = True
    else:
        result['information_fresh'] = False
    return result


def find_camera_info_in_log(camera_name):
    grep = subprocess.Popen(('grep', f'SBIGCamera({camera_name}) - ', logfile), stdout=subprocess.PIPE)
    tail = subprocess.Popen(('tail', '-1'), stdin=grep.stdout, stdout=subprocess.PIPE)
    output = tail.communicate()[0].decode().strip()
    result = ast.literal_eval(re.sub(r'^.*?{', '{', output))
    result['information_age_s'] = seconds_since_info_refresh(output)
    if result['information_age_s'] < 10:
        result['information_fresh'] = True
    else:
        result['information_fresh'] = False
    return result


def find_powerbox_info_in_log():
    grep = subprocess.Popen(('grep','PegasusPowerbox - {', logfile), stdout=subprocess.PIPE)
    tail = subprocess.Popen(('tail', '-1'), stdin=grep.stdout, stdout=subprocess.PIPE)
    output = tail.communicate()[0].decode().strip()
    result = ast.literal_eval(re.sub(r'^.*?{', '{', output))
    result['information_age_s'] = seconds_since_info_refresh(output)
    if result['information_age_s'] < 10:
        result['information_fresh'] = True
    else:
        result['information_fresh'] = False
    return result

def find_lens_info_in_log():
    grep = subprocess.Popen(('grep','Canon - {', logfile), stdout=subprocess.PIPE)
    tail = subprocess.Popen(('tail', '-1'), stdin=grep.stdout, stdout=subprocess.PIPE)
    output = tail.communicate()[0].decode().strip()
    result = ast.literal_eval(re.sub(r'^.*?{', '{', output))
    result['information_age_s'] = seconds_since_info_refresh(output)
    if result['information_age_s'] < 10:
        result['information_fresh'] = True
    else:
        result['information_fresh'] = False
    return result
