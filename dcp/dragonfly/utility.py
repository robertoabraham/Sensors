import os
import re
import glob
import time
import traceback
import subprocess
import shlex
import pandas as pd    
from PIL import Image, ImageDraw, ImageFont
from astropy.io import fits
import numpy as np


def latest_fits_file(dirname):
    list_of_files = glob.glob(os.path.join(dirname,'*.fits')) 
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file

def fits_files_in_range(directory, start, end):
    files = []
    for filename in os.listdir(directory):
        basename, ext = os.path.splitext(filename)        
        if '.fits' in ext:
            file_number = int(basename.split("/")[-1].split("_")[1])
            if file_number >= start and file_number <= end:
                files.append(os.path.join(directory,filename))
    # Sort the filenames so that files with _3_ come before _23_, etc.
    files = sorted(files, key=lambda s: int(re.search(r'_(\d+)_', s).group(1)))            
    return(files)
     
def highest_fits_sequence_number(serno:str, directory:str) -> str:
    fileno_max = None
    for filename in os.listdir(directory):
        try:
            basename, ext = os.path.splitext(filename)        
            if '.fits' in ext:
                fileno = int(re.search(r'' + serno +'_(\d+)_',basename).group(1))
                if fileno_max is None or fileno > fileno_max:
                    fileno_max = fileno
        except AttributeError:
            pass    
    return(fileno_max)

def summarize_directory(directory, start=0, end=100000,
                    keys=['DATE','EXPTIME','FOCUSPOS','CCD-TEMP','NAXIS1','NAXIS2'],
                    full_path=False):
    """Returns a DataFrame with header information for a set of FITS files in a specified directory.

    Args:
        directory (string): Path to directory
        start (int, optional): Starting file number. Defaults to 0.
        end (int, optional): Ending file number. Defaults to 100000.
        keys (list, optional): List of FITS keywords to summarize. Defaults to ['DATE','EXPTIME','FOCUSPOS','CCD-TEMP','NAXIS1','NAXIS2'].
        full_path (bool, optional): Include full path in filename. Defaults to False.
    """
    
    # These will be the dataframe keys.
    new_keys = keys.copy()
    new_keys.insert(0,'FILENUM') # Put this at the beginning
    new_keys.append('FILENAME')  # Put this at the end
    
    # Iterate over all the files and create an array with all the information.
    files = fits_files_in_range(directory, start, end)
    rows = []
    for filename in files:
        basename, ext = os.path.splitext(filename)
        file_number = int(basename.split("/")[-1].split("_")[1])
        new_row = {}
        new_row['FILENUM'] = file_number
        hdul = fits.open(filename)
        hdr = hdul[0].header
        for key in keys:       
            new_row[key] = hdr[key]
        if not full_path:
            new_row['FILENAME'] = os.path.basename(filename)
        else:
            new_row['FILENAME'] = filename
        rows.append(new_row)
    df = pd.DataFrame(rows, columns = new_keys)
    return(df)

def create_banner_image(filename):
    """Creates a PNG image with the specified properties.

    Args:
        filename (str): The name of the image file to create.
    """
    font_name = "/home/dragonfly/miniforge3/envs/active_optics/fonts/UbuntuMono-R.ttf"
    img = Image.new('RGB', (200, 200), color='white')
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_name, size=14)
    text = "File not found."
    x = 40
    y = 90
    draw.text((x, y), text, fill='black', font=font)
    img.save(filename)

def display_png(image_file):
    """Display a PNG image as a background process using sxiv.

    Args:
        image_file (string): Path to a PNG file.
    """
    
    if not os.path.exists(image_file):
        create_banner_image(image_file)
    
    # If sxiv is not already displaying this PNG, display it in the background.
    # Note that sxiv auto-refreshes when the image changes on disk, so we don't
    # want to run sxiv twice.
    check_line = f"pgrep -f 'sxiv {image_file}'"
    command_line = f"nohup /usr/bin/sxiv {image_file} &"
    try:
        subprocess.check_output(shlex.split(check_line))
    except subprocess.CalledProcessError:
        # Process to display the image is not already running, so start it in
        # the background.
        try:
            subprocess.Popen(shlex.split(command_line),
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
            print("Could not start sxiv.")

def find_line_in_subprocess_stdout(stdout_data, string_to_match):
    """
    find_line_in_subprocess_stdout - find matching line an object returned by a subprocess command.
    """
    try:
        # Expect a byte string with a bunch of newline-separated lines. The line
        # we are interested in begins with the word 'Result'. So we will split the
        # byte string into lines and search for the line containing 'Result'.
        matching_line = [line for line in str(stdout_data.stdout).split('\\n') if string_to_match in line][0]
        return matching_line
    except:
        raise ValueError

def get2x2MatrixDeternminant(m):
    if len(m) != 2:
        raise ValueError
    return m[0][0]*m[1][1]-m[0][1]*m[1][0]

def get2x2MatrixInverse(m):
    if len(m) != 2:
        raise ValueError
    determinant = get2x2MatrixDeternminant(m)
    return [[m[1][1]/determinant, -1*m[0][1]/determinant], [-1*m[1][0]/determinant, m[0][0]/determinant]]

def convert_to_number_or_bool_or_None(numstring):
    "Converts a string to a number or bool, if it makes sense to do so. Otherwise, just return the string."
    try:
        if numstring == None:
            return numstring 

        if 'true' in numstring:
            return True

        if 'false' in numstring:
            return False
        
        if 'null' in numstring:
            return None

        if '.' in numstring:
            return(float(numstring))
        else:
            return(int(numstring)) 
     
    except ValueError:
        return(numstring)
    except TypeError:
        return(numstring)

class FileModificationTimeWatcher:
    """
    Tweaked from https://www.thediggledocs.co.uk/blog/2023-02-20_detecting-file-modification/
    """
    def __init__(self, watch_path, callback):
        self.watch_path = watch_path
        self.callback = callback
        self.modification_time_at_start = os.path.getmtime(watch_path)
        self.counter = 0

    def start(self):
        try:
            while True:
                time.sleep(1)
                modified = os.path.getmtime(self.watch_path)
                if modified != self.modification_time_at_start:
                    self.modification_time_at_start = modified
                    self.counter = -1
                    if self.callback():
                        break
                else:
                    self.counter += 1
        except Exception as e:
            print(traceback.format_exc())


