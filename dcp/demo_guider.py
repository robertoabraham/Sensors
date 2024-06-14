from dragonfly.hardware.diffraction_limited.gateway import DLAPIGateway
from dragonfly.hardware.diffraction_limited.camera import DLAPICamera
from dragonfly.hardware.canon import CanonEFLens
from dragonfly.hardware.guider import ActiveOpticsGuider
from dragonfly import utility
from dragonfly.control import tools

# Connect to the hardware
print("Creating objects.")
gw = DLAPIGateway(verbose=True)
sc = DLAPICamera(gw, 'starchaser', verbose=True)
aluma = DLAPICamera(gw, 'aluma', verbose=True)
lens = CanonEFLens()
guider = ActiveOpticsGuider(sc, lens, verbose=True)
print("Connecting to hardware.")
sc.connect()
aluma.connect()
lens.connect()
guider.connect()

if not guider.state['is_calibrated']:
    print("Calibrating the guider.")
    guider.calibrate()

# Start guiding
print("Start guiding.")
guider.set_exposure_time(0.1)
guider.start_guiding()

# guider.time_series.clear()
# utility.display_png('/tmp/guiding.png')
# guider.time_series.plot('/tmp/guiding.png')

# guider.stop_guiding()

