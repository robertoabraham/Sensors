from datetime import datetime
from scipy.interpolate import interp1d
import json
import time
import random
import shlex
import subprocess
import numpy as np
import matplotlib
matplotlib.use('svg')
import matplotlib.pyplot as plt
from matplotlib import patches
import matplotlib.dates as mdates

class TimeSeries:

    def __init__(self):
        self.time_values = []
        self.x_values = []
        self.y_values = []
        self.output_filename = None

    def clear(self):
        self.time_values = []
        self.x_values = []
        self.y_values = []
        self.output_filename = None

    def add_point(self, x: float = None, y: float = None):

        if len(self.time_values) == 0:
            start_time = datetime.now()
            self.output_filename = start_time.strftime("%Y-%m-%d_%Hh%Mm%Ss.json")
        self.time_values.append(datetime.now())
        if x is None:
            x = random.gauss(0, 1)
        if y is None:
            y = random.gauss(0, 1)
        self.x_values.append(x)
        self.y_values.append(y)

    def plot(self, file=None):
        plt.clf()
        fig, (ax1, ax2) = plt.subplots(nrows=1, ncols=2, num=0)
        fig.set_size_inches(10, 5)

        # Scatter plot on the left
        circle1 = patches.Circle((0.0, 0.0), radius=2.0, color='green', alpha=0.1)
        circle2 = patches.Annulus((0.0, 0.0), r=4.0, width=2, color='yellow', alpha=0.1)
        circle3 = patches.Annulus((0.0, 0.0), r=6.0, width=2, color='red', alpha=0.1)
        ax1.add_patch(circle1)
        ax1.add_patch(circle2)
        ax1.add_patch(circle3)
        ax1.scatter(self.x_values, self.y_values,
                    c='black', marker='o', alpha=.3)
        ax1.set(xlabel=r'$\Delta X$ (arcsec)',
                ylabel=r'$\Delta Y$ (arcsec)',
                title='IS Corrections')
        ax1.axis('equal')
        ax1.axhline(y=0, color='k', linestyle=':')
        ax1.axvline(x=0, color='k', linestyle=':')
        ax2.plot(self.time_values, self.x_values, label=r'$\Delta X$ (arcsec)')
        ax2.plot(self.time_values, self.y_values, label=r'$\Delta Y$ (arcsec)')
        ax2.scatter(self.time_values, self.x_values)
        ax2.scatter(self.time_values, self.y_values)
        ax2.set(xlabel='Time',
                ylabel='Correction (arcsec)',
                title='IS Corrections vs. Time')
        ax2.grid(True, which='both')
        ax2.legend()
        date_fmt = mdates.DateFormatter('%H:%M:%S')
        ax2.xaxis.set_major_formatter(date_fmt)
        plt.setp(ax2.get_xticklabels(), rotation=30, horizontalalignment='right')
        if file is None:
            plt.show()
        else:
            # Create an image. Then display it with `sxiv` if you want
            # the image to auto-refresh.
            plt.savefig(file)

    def save(self, filename=None):
        data = {
            'time_values': [t.isoformat() for t in self.time_values],
            'x_values': self.x_values,
            'y_values': self.y_values
        }
        if filename is None:
            filename = self.output_filename
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filename):
        with open(filename, 'r') as f:
            data = json.load(f)
        time_values = [datetime.fromisoformat(t) for t in data['time_values']]
        x_values = data['x_values']
        y_values = data['y_values']
        ts = cls()
        ts.time_values = time_values
        ts.x_values = x_values
        ts.y_values = y_values
        ts.output_filename = filename
        return ts


def demo():

    data_file = "/tmp/demo.json"
    image_file = "/tmp/demo.png"

    print("Creating a TimeSeries()")
    t = TimeSeries()
    npts = 100
    i = 0
    while i < npts:
        print("Adding point.")
        t.add_point()
        time.sleep(0.1)
        i = i + 1
    print("Plotting data.")
    t.plot(image_file)

    # If sxiv is not already displaying this PNG, display it.
    # Note that sxiv auto-refreshes when the image changes on disk.
    check_line = f"pgrep -f 'sxiv {image_file}'"
    command_line = f"nohup /usr/bin/sxiv {image_file} &"
    try:
        subprocess.check_output(shlex.split(check_line))
        print("Image is already being displayed (and auto-refreshing).")
    except subprocess.CalledProcessError:
        # start the program in the background
        subprocess.Popen(shlex.split(command_line))
        print(f"Executed {command_line} to display the image.")

    print("Saving the dataset.")
    t.save(data_file)
    print("Clearing the dataset from memory.")
    t.clear()
    print("Plotting the empty dataset")
    t.plot(image_file)
    print("Reloading the dataset from disk.")
    t = TimeSeries.load(data_file)
    print("Replotting the dataset")
    t.plot(image_file)
