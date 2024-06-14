import pytest
import time
import os
import numpy as np

from astropy.io import fits

from dragonfly.hardware.diffraction_limited.gateway import DLAPIGateway
from dragonfly.hardware.diffraction_limited.camera import DLAPICamera

def test_connect(provide_dragonfly_objects):
    gw, sc, aluma, lens = provide_dragonfly_objects
    aluma.connect()
    assert aluma.state['is_connected'] == True

def test_file_creation(provide_dragonfly_objects):
    gw, sc, aluma, lens = provide_dragonfly_objects

    temporary_filename = '/tmp/test_bias.fits'
    if os.path.exists(temporary_filename):
        os.remove(temporary_filename)
    aluma.connect()
    aluma.expose(0, 'bias', filename = temporary_filename)
    assert os.path.exists(temporary_filename)

def test_single_bias(provide_dragonfly_objects):
    gw, sc, aluma, lens = provide_dragonfly_objects

    temporary_filename = '/tmp/test_bias.fits'
    if os.path.exists(temporary_filename):
        os.remove(temporary_filename)
    aluma.connect()
    aluma.expose(0, 'bias', filename = temporary_filename)
    hdul = fits.open(temporary_filename)
    hdr = hdul[0].header
    data = hdul[0].data
    mean = round(np.mean(data),3)
    print(f"Bias level: {mean}")
    assert(mean > 900 and mean < 1100)
    
def test_readnoise(provide_dragonfly_objects):
    gw, sc, aluma, lens = provide_dragonfly_objects

    temporary_filename1 = '/tmp/test_bias_1.fits'
    if os.path.exists(temporary_filename1):
        os.remove(temporary_filename1)
        
    temporary_filename2 = '/tmp/test_bias_2.fits'
    if os.path.exists(temporary_filename2):
        os.remove(temporary_filename2)
        
    aluma.connect()
    aluma.expose(0, 'bias', filename = temporary_filename1)
    aluma.expose(0, 'bias', filename = temporary_filename2)

    hdul1 = fits.open(temporary_filename1)
    data1 = np.float32(hdul1[0].data)
    hdul1.close()
    mean1 = np.mean(data1)
    sigma1 = np.std(data1)
    print(f"Mean for first frame: {round(mean1,3)}")
    print(f"Sigma for first frame: {round(sigma1,3)}")

    hdul2 = fits.open(temporary_filename2)
    data2 = np.float32(hdul2[0].data)
    hdul2.close()
    mean2 = np.mean(data2)
    sigma2 = np.std(data2)
    print(f"Mean for second frame: {round(mean2,3)}")
    print(f"Sigma for second frame: {round(sigma2,3)}")
    
    diff = data2 - data1
    mean = np.mean(diff)
    sigma = np.std(diff)
    print(f"Mean for difference: {round(mean,3)}")
    print(f"Sigma for difference: {round(sigma,3)}")
    
    gain = aluma.get_sensor_calibration()['electronic_gain']
    print(f"Gain: {round(gain,3)}")
            
    readnoise = sigma*gain/np.sqrt(2)
    print(f"Readnoise: {round(readnoise,3)}")
    assert(readnoise > 3 and readnoise < 6)

# @pytest.mark.skip(reason="This test is optional for now.")
def test_for_consistent_biases(provide_dragonfly_objects):
    gw, sc, aluma, lens = provide_dragonfly_objects
    aluma.connect()
    print("Setting 2x2 binning.")
    aluma.set_binning(2)
    print("Taking 1000 bias frames and making sure they are consistent.")
    means = []
    sigmas = []
    for i in range(1000): 
        temporary_filename = '/tmp/test_bias.fits'
        if os.path.exists(temporary_filename):
            os.remove(temporary_filename)
        aluma.expose(0, 'bias', filename = temporary_filename)
        hdul = fits.open(temporary_filename)
        hdr = hdul[0].header
        data = np.float32(hdul[0].data)
        hdul.close()
        mean = np.mean(data)
        sigma = np.std(data)
        means.append(mean)
        sigmas.append(sigma)
        print(f"Frame: {i}  Bias level: {round(mean,3)}  Sigma: {round(sigma,3)}")
    std_mean = np.std(means)
    print(f"Standard deviation of the means: {round(std_mean,3)}")
    assert(std_mean < 1.0) 
