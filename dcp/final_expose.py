#!/usr/bin/env python3

import sys
import argparse
import subprocess
from tabnanny import verbose
import time

#read in command line arguments
command_list = [
    '',
    'Calls dfcore expose',
    'Exposes the camera, checks if download was successful, if not, then redownloads',
    'Use dfcore directly for commands like cool and list'
]

parser = argparse.ArgumentParser()

parser.add_argument("-v", "--verbose", default=False, action="store_true", 
                    help="increase output verbosity (default = False)")
parser.add_argument("-w", "--wait_time", type=float,  
                    help="wait time in seconds before camera communication begins (default = 2)")

parser.add_argument("--camera", type=int, 
                    help="Which camera to control (see `dfcore list`).Defaults to the first non-Starchaser camera.")

parser.add_argument("--duration", type=float, 
                    help="Duration of exposure in seconds.", required=True)

parser.add_argument("--savedir", type=str , 
                    help="Directory to save exposure to. Defaults to the current directory where the program is run.")

parser.add_argument("--filename", type=str , 
                    help="Filename to save exposure to. If not passed, automatically determines the filename"+
                    " based on number of images in the save directory, the file type, and the serial number of the camera.")

parser.add_argument("--dark",  default=False, action="store_true", 
                    help="Take a dark frame")

parser.add_argument("--bias",  default=False, action="store_true", 
                    help="Take a bias frame (shortest possible exposure). Overrides --duration")

parser.add_argument("--flat",  default=False, action="store_true", 
                    help="Take a flat frame. This is the same as a light frame except for the file naming and header values")

parser.add_argument("--guider",  default=False, action="store_true", 
                    help="Take an exposure with the off-axis guider")

parser.add_argument("--binx", type=int, 
                    help="Amount of binning for the x axis. Defaults to 1.")

parser.add_argument("--biny", type=int, 
                    help="Amount of binning for the y axis. Defaults to 1.")
                    
parser.add_argument("--n", type=int, 
                    help="Number of exposures to take with current settings. Defaults to 1.")

parser.add_argument("--disable_overscan", default=False, action="store_true", 
                    help="Disable overscan")

parser.add_argument("--n_redownload", default=1, type=int, 
                    help="Number of redownload attemps to take with current settings. Defaults to 1.")

parser.add_argument("--header", nargs=2, action='append',
                    help= "key and value")

parser.add_argument("--focus_pos", type=int, 
                    help="Current focus position (will be written to FITS file). Defaults to -1.")

#pass on args to dfcore
args = parser.parse_args()
# command_line = "./dfcore expose"
command_line = "/home/dragonfly/dragonfly-arm/core/dfcore expose"
# command_line = "python tester.py" #seery's tester script, ignore
command_list = command_line.split()
if args.wait_time is not None:
    command_list.append("--wait_time %.1f"%args.wait_time)
if args.camera is not None:
    command_list.append("--camera %i"%args.camera)
if args.duration is not None:
    command_list.append("--duration %.1f"%args.duration)
if args.savedir is not None:
    command_list.append("--savedir %s"%args.savedir)
if args.filename is not None:
    command_list.append("--filename %s"%args.filename)
if args.dark:
    command_list.append("--dark")
if args.bias:
    command_list.append("--bias")
if args.flat:
    command_list.append("--flat")
if args.guider:
    command_list.append("--guider")
if args.binx is not None:
    command_list.append("--binx %i"%args.binx)
if args.biny is not None:
    command_list.append("--biny %i"%args.biny)
if args.n is not None:
    command_list.append("--n %i"%args.n)
if args.disable_overscan:
    command_list.append("--disable_overscan")
    command_list.append("1")
if args.header is not None:
    for headerpair in args.header:
        command_list.append("--header %s %s"%(headerpair[0], headerpair[1]))
if args.focus_pos is not None:
    command_list.append("--focus_pos %i"%args.focus_pos)

command_string = " ".join(command_list)

def expose_command(verbose=args.verbose, prefix=""):
    command_string = " ".join(command_list)
    if verbose:
        print(prefix + "Running: {}".format(command_string))
    result = ''
    try:
        result = subprocess.run(command_string, capture_output=True, check=False, shell=True)
    except subprocess.CalledProcessError:
        print('exposure failed')
    return result

def redownload_command():
    command_list.append("--downloadlastimage true")
    command_string = " ".join(command_list)
    print("Image failed to download, waiting 5s")
    time.sleep(5)
    print("Now trying downloadlastimage")
    if verbose:
        print("" + "Running: {}".format(command_string))
    result = ''
    try:
        result = subprocess.run(command_string, capture_output=True, check=False, shell=True)
    except subprocess.CalledProcessError:
        print('download last image failed')
    except subprocess.TimeoutExpired:
        print('timed out. Exposure failed')
    return result

def main():
    result = expose_command()
    i=1
    # print(result.stdout)
    if args.verbose == True:
        # print(command_list)
        # print(command_string)
        print("RESULT: ", result)
        print()
        print()
    while (result.returncode!=0):
        # note: for every error that dfcore throws, it will try to redownload the image
        #  so if taking the image itself was unsuccessful, it will redownload the last successful image
        #  ***TO FIX LATER *** SC 2023-05-31
        if (i>args.n_redownload):
            print('Error. Downloading last image unsuccessful')
            return(1)
        time.sleep(5)
        i=i+1
        result = redownload_command()
        if args.verbose == True:
            print("RESULT: ", result)
            print()
            print()
    print(result.stdout.decode())
    return(0)

if __name__ == '__main__':
    main()
