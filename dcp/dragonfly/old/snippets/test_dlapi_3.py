from datetime import datetime, timedelta
import time

from dragonfly import find
from dragonfly.hardware.pegasus import PegasusPowerbox
from dragonfly.hardware.diffraction_limited.gateway import DLAPIGateway
from dragonfly.hardware.diffraction_limited.camera import DLAPICamera
from astropy.io import fits

print("Connecting to powerbox...")
pb = PegasusPowerbox(find.find_powerbox_serial_port())
pb.connect()

print("Connecting to cameras...")
gw = DLAPIGateway(verbose=True)
sc = DLAPICamera(gw, 'starchaser', verbose=True)
aluma = DLAPICamera(gw, 'aluma', verbose=True)
sc = DLAPICamera(gw, 'starchaser', verbose=True)
aluma.connect()
sc.connect()
time.sleep(0.5)

print("Exposing Aluma")
aluma.expose(0.1,'light', checksum=True, debug=True)