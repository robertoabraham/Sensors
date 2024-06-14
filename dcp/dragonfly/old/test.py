import sys
import re
import subprocess
import logging
from dragonfly import lens

log = logging.getLogger('team_dragonfly')
log.addHandler(logging.NullHandler())

# If you want to see information messages in iPython interactive sessions:
# import logging
# log = logging.getLogger('team_dragonfly')
# log.setLevel(logging.INFO)

if (sys.version_info[0] != 3):
    raise Exception("Sorry - I only work under python3")

class bcolors:
    HEADER =    '\033[95m'
    OKBLUE =    '\033[94m'
    OKCYAN =    '\033[96m'
    OKGREEN =   '\033[92m'
    WARNING =   '\033[93m'
    FAIL =      '\033[91m'
    ENDC =      '\033[0m'
    BOLD =      '\033[1m'
    UNDERLINE = '\033[4m'

# Note: tests need to be run in a specific order.
tests = ['lp_1', 'la_1', 'mf_1', 'pf_1', 'pf_2']

low_level_command_test = {}

# Lens presence.
low_level_command_test['lp_1'] = {
    'description':   'Test whether the software sees the lens.',
    'command':       'lp',
    'prior_command': None,
    'post_command':  None,
    'check_prefix':  'Result:',
    'spi_sent':      None,
    'spi_received':  None,
    'result_min':    None,
    'result_max':    None,
    'result_regex': 'Lens is connected!',
    'timeout':       5
}

# Learn the lens range.
low_level_command_test['la_1'] = {
    'description':   'Test whether the lens range can be defined.',
    'command':       'la',
    'prior_command': None,
    'post_command':  None,
    'check_prefix':  'Received:',
    'spi_sent':      [0x5, 0xC0, 0x0, 0x0, 0x6, 0xC0, 0x0, 0x0],
    'spi_received':  None,
    'result_min':    None,
    'result_max':    None,
    'result_regex':  None,
    'timeout':       10
}

# Set the lens zeropoint
low_level_command_test['sf0_1'] = {
    'description':   'Test whether the lens zeropoint can be defined.',
    'command':       'sf0',
    'prior_command': None,
    'post_command':  None,
    'check_prefix':  'Received:',
    'spi_sent':      [0xC],
    'spi_received':  None,
    'result_min':    None,
    'result_max':    None,
    'result_regex':  None,
    'timeout':       10
}

# Notes:
#   1. Check camera focus operation using relative movements because
#      inside the arduino codebase all movements are relative. 
#   2. Set the prior command to something intermediate to the camera 
#      range to make sure we don't drive the lens into end stops.
low_level_command_test['mf_1'] = {
    'description':   'Test whether relative movement commands can be sent.',
    'command':       'mf 1123',
    'prior_command': 'fa 10000',
    'post_command':  None,
    'check_prefix':  'Received:',
    'spi_sent':      [0x44, 0x4, 0x63],
    'spi_received':  None,
    'result_min':    None,
    'result_max':    None,
    'timeout':       10
}

# Check lens response at two separate positions.
low_level_command_test['pf_1'] = {
    'description':   'Test whether lens can be moved and then report its position correctly (near focus).',
    'command':       'pf',
    'prior_command': 'fa 1055',
    'post_command':  None,
    'check_prefix':  'Result:',
    'spi_sent':      None,
    'spi_received':  None,
    'result_min':    None,
    'result_max':    None,
    'result_regex':  'Focus position: 105*',
    'timeout':       10
}

# Check lens response at two separate positions.
low_level_command_test['pf_2'] = {
    'description':   'Test whether lens can be moved and then report its position correctly (far focus).',
    'command':       'pf',
    'prior_command': 'fa 19055',
    'post_command':  None,
    'check_prefix':  'Result:',
    'spi_sent':      None,
    'spi_received':  None,
    'result_min':    None,
    'result_max':    None,
    'result_regex':  'Focus position: 1905*',
    'timeout':       10
}

def run_test(test_to_run, verbose=False):
    passed = True
    command_data = low_level_command_test[test_to_run]
    print(command_data['description'])

    # Run the command which sets up the test we're interested in running.
    result = lens.run_command(command_data['prior_command'], verbose, prefix='(Setup) ')

    # Run the command which we wish to test.
    result = lens.run_command(command_data['command'], verbose)

    # Analyze the results and determine whether or not the test passed or failed
    # on the basis of multiple criteria which must all be met.

    # Pass/fail on the basis of the returned string.
    if 'Result:' in command_data['check_prefix']:
        if command_data['result_regex'] is not None:
            print("  Criterion - The lens returned the correct result string. ", end='')
            if re.search(command_data['result_regex'], result.stdout.decode()):
                print(f"{bcolors.OKGREEN}\N{check mark}{bcolors.ENDC}")
            else:
                passed = False
                print(f"{bcolors.FAIL}\N{ballot x}{bcolors.ENDC}")

    # Pass/fail on the basis of the hexadecimal numbers sent/received to the lens
    if 'Received:' in command_data['check_prefix']:
        result_list = list(filter(None,[i.strip() for i in result.stdout.decode().split('\n')]))
        sent_lines = list(filter(lambda line: 'Received: SPI sent' in line, result_list))
        sent_numbers = [int(line.replace('Received: SPI sent: ','0x'),base=16) for line in sent_lines]
        received_lines = list(filter(lambda line: 'Received: SPI received' in line, result_list))
        received_numbers = [int(line.replace('Received: SPI received: ','0x'),base=16) for line in received_lines]
        if command_data['spi_sent'] is not None:
            print("  Criterion - correct hexadecimal numbers were sent to the lens. ", end='')
            if sent_numbers == command_data['spi_sent']:
                print(f"{bcolors.OKGREEN}\N{check mark}{bcolors.ENDC}")
            else:
                if passed:
                    passed = False
                print(f"{bcolors.FAIL}\N{ballot x}{bcolors.ENDC}")
        if command_data['spi_received'] is not None:
            print("  Criterion - correct hexadecimal numbers were returned by the lens. ", end='')
            if received_numbers == command_data['spi_received']:
                print(f"{bcolors.OKGREEN}\N{check mark}{bcolors.ENDC}")
                if passed:
                    passed = False
            else:
                print(f"{bcolors.FAIL}\N{ballot x}{bcolors.ENDC}")

    
    if passed:
        print(f"{bcolors.OKGREEN}  Test passed.{bcolors.ENDC}")
    else:
        print(f"{bcolors.FAIL}  Test failed.{bcolors.ENDC}")

    return passed
