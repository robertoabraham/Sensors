import pytest
import time
import os
import numpy as np

from astropy.io import fits

from dragonfly.hardware.diffraction_limited.gateway import DLAPIGateway
from dragonfly.hardware.diffraction_limited.camera import DLAPICamera

def test_connect(provide_dragonfly_objects):
    gw, sc, aluma, lens = provide_dragonfly_objects
    sc.connect()
    assert sc.state['is_connected'] == True

def test_file_creation(provide_dragonfly_objects):
    gw, sc, aluma, lens = provide_dragonfly_objects

    temporary_filename = '/tmp/test_bias.fits'
    if os.path.exists(temporary_filename):
        os.remove(temporary_filename)
    sc.connect()
    sc.expose(0, 'bias', filename = temporary_filename)
    assert os.path.exists(temporary_filename)

def test_single_bias(provide_dragonfly_objects):
    gw, sc, aluma, lens = provide_dragonfly_objects

    temporary_filename = '/tmp/test_bias.fits'
    if os.path.exists(temporary_filename):
        os.remove(temporary_filename)
    sc.connect()
    sc.expose(0, 'bias', filename = temporary_filename)
    hdul = fits.open(temporary_filename)
    hdr = hdul[0].header
    data = hdul[0].data
    mean = round(np.mean(data),3)
    print(f"Bias level: {mean}")
    assert(mean > 40 and mean < 60)

def test_multiple_bias(provide_dragonfly_objects):
    gw, sc, aluma, lens = provide_dragonfly_objects
    sc.connect()

    print("Taking 5 bias frames")
    for i in range(5): 
        temporary_filename = '/tmp/test_bias.fits'
        if os.path.exists(temporary_filename):
            os.remove(temporary_filename)
        sc.expose(0, 'bias', filename = temporary_filename)
        hdul = fits.open(temporary_filename)
        hdr = hdul[0].header
        data = hdul[0].data
        mean = round(np.mean(data),3)
        print(f"Bias level: {mean}")
        assert(mean > 40 and mean < 60) 
