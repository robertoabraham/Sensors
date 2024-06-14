import pytest

from dragonfly import find
from dragonfly.hardware.diffraction_limited.gateway import DLAPIGateway
from dragonfly.hardware.diffraction_limited.camera import DLAPICamera
from dragonfly.hardware.canon import CanonEFLens

@pytest.fixture
def provide_dragonfly_objects():
    gw = DLAPIGateway(verbose=True)
    sc = DLAPICamera(gw, 'starchaser', verbose=True)
    aluma = DLAPICamera(gw, 'aluma', verbose=True)
    lens = CanonEFLens()
    return gw, sc, aluma, lens
