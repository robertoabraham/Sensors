import pytest
import time

from dragonfly.hardware.diffraction_limited.gateway import DLAPIGateway
from dragonfly.hardware.diffraction_limited.camera import DLAPICamera
from dragonfly.hardware.canon import CanonEFLens

def test_instantiation(provide_dragonfly_objects):
    gw, sc, aluma,lens = provide_dragonfly_objects
    assert isinstance(gw, DLAPIGateway)
    assert isinstance(sc, DLAPICamera)
    assert isinstance(aluma, DLAPICamera)
    assert isinstance(lens, CanonEFLens)
