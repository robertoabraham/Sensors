from datetime import datetime
import json
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
import hashlib
import pandas as pd

from dragonfly import utility

class ImagingRun:

    def __init__(self):
        self.filenames = []
        self.checksums = []
        self.time_values = []
        self.skylevel_values = []
        self.date_values = []
        self.exptime_values = []
        self.focuspos_values = []
        self.ccd_temp_values = []
        self.naxis1_values = []
        self.naxis2_values = []
        self.checksum_values = []
        self.output_filename = None

    def clear(self):
        self.filenames = []
        self.checksums = []
        self.time_values = []
        self.skylevel_values = []
        self.date_values = []
        self.exptime_values = []
        self.focuspos_values = []
        self.ccd_temp_values = []
        self.naxis1_values = []
        self.naxis2_values = []
        self.checksum_values = []
        self.output_filename = None

    def add_image(self, filename:str):
        keys=['DATE','EXPTIME','FOCUSPOS','CCD-TEMP','NAXIS1','NAXIS2']
        
        if len(self.time_values) == 0:
            start_time = datetime.now()
            self.output_filename = start_time.strftime("%Y-%m-%d_%Hh%Mm%Ss.json")
        self.time_values.append(datetime.now())
        self.filenames.append(filename)
        hdu = fits.open(filename)
        hdr = hdu[0].header
        data = hdu[0].data
        hdu.close()
        self.date_values.append(hdr['DATE'])
        self.exptime_values.append(hdr['EXPTIME'])
        self.focuspos_values.append(hdr['FOCUSPOS'])
        self.ccd_temp_values.append(hdr['CCD-TEMP'])
        self.naxis1_values.append(hdr['NAXIS1'])
        self.naxis2_values.append(hdr['NAXIS2'])
        (sky_mean, sky_median, sky_sigma) = sigma_clipped_stats(data, sigma=2, maxiters=5)
        self.skylevel_values.append(sky_median)
        self.checksum_values.append(self.checksum(filename))
        
    def checksum(self, filename):
        return hashlib.md5(open(filename,'rb').read()).hexdigest()

    def save(self, filename=None):
        data = {
            'time_values': [t.isoformat() for t in self.time_values],
            'filenames': self.filenames,
            'date_values': self.date_values,
            'exptime_values': self.exptime_values,
            'focuspos_values': self.focuspos_values,
            'ccd_temp_values': self.ccd_temp_values,
            'naxis1_values': self.naxis1_values,
            'naxis2_values': self.naxis2_values,
            'skylevel_values': self.skylevel_values,
            'checksum_values': self.checksum_values
        }
        if filename is None:
            filename = self.output_filename
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
            
    def len(self):
        """Return the number of images in the dataset.

        Returns:
            int: number of images in the dataset_
        """
        return len(self.filenames)
    
    def to_dataframe(self):
        """Creates a pandas DataFrame from the property lists in the class."""
        data = {
            'time': self.time_values,
            'filename': self.filenames,
            'date': self.date_values,
            'exptime': self.exptime_values,
            'focuspos': self.focuspos_values,
            'ccd_temp': self.ccd_temp_values,
            'naxis1': self.naxis1_values,
            'naxis2': self.naxis2_values,
            'skylevel': self.skylevel_values,
            'checksum': self.checksum_values
        }
        df = pd.DataFrame(data)
        return df

    @classmethod
    def load(cls, filename):
        """Creates an ImagingRun object from a JSON filename."""
        with open(filename, 'r') as f:
            data = json.load(f)
        time_values = [datetime.fromisoformat(t) for t in data['time_values']]
        ts = cls()
        ts.time_values = time_values
        ts.filenames = data['filenames']
        ts.date_values = data['date_values']
        ts.exptime_values = data['exptime_values']
        ts.focuspos_values = data['focuspos_values']
        ts.ccd_temp_values = data['ccd_temp_values']
        ts.naxis1_values = data['naxis1_values']
        ts.naxis2_values = data['naxis2_values']
        ts.skylevel_values = data['skylevel_values']
        ts.checksum_values = data['checksum_values']
        ts.output_filename = filename
        return ts

    @classmethod
    def from_dataframe(cls, df):
        """Creates an ImagingRun object from a pandas DataFrame."""
        ts = cls()
        ts.time_values = pd.to_datetime(df['time'])
        ts.filenames = df['filename'].tolist()
        ts.date_values = pd.to_datetime(df['date'])
        ts.exptime_values = df['exptime'].tolist()
        ts.focuspos_values = df['focuspos'].tolist()
        ts.ccd_temp_values = df['ccd_temp'].tolist()
        ts.naxis1_values = df['naxis1'].tolist()
        ts.naxis2_values = df['naxis2'].tolist()
        ts.skylevel_values = df['skylevel'].tolist()
        ts.checksum_values = df['checksum'].tolist()
        return ts

def demo():

    data_file = "/tmp/ir_demo.json"
    new_data_file = "/tmp/ir_demo_new.json"
    datadir = "/home/dragonfly/dragonfly-arm/active_optics/data/focus_ha"
    print("Starting a simualated imaging run")
    ir = ImagingRun()
    df = utility.summarize_directory(datadir,30,40,full_path=True)
    filenames = df.loc[:,"FILENAME"].to_list()
    for filename in filenames:
        print(f"Adding {filename} to the dataset.")
        ir.add_image(filename)
    print(f"Dataset contains {ir.len()} images.")
    print("Saving the dataset.")
    ir.save(data_file)
    print("Clearing the dataset from memory.")
    ir.clear()
    print(f"Dataset contains {ir.len()} images.")
    print("Reloading the dataset from disk.")
    ir = ImagingRun.load(data_file)
    print("Saving the dataset.")
    ir.save(new_data_file)   
    print(f"Dataset contains {ir.len()} images.")
    print("Converting the dataset to a pandas DataFrame and printing the first few rows.")
    df = ir.to_dataframe()
    print(df.head())