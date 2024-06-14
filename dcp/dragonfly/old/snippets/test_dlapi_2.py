from datetime import datetime, timedelta
import time

from dragonfly import find
from dragonfly.hardware.pegasus import PegasusPowerbox
from dragonfly.hardware.diffraction_limited.gateway import DLAPIGateway
from dragonfly.hardware.diffraction_limited.camera import DLAPICamera
from astropy.io import fits

pb = PegasusPowerbox(find.find_powerbox_serial_port())
pb.connect()

gw = DLAPIGateway(verbose=True)
sc = DLAPICamera(gw, 'starchaser', verbose=True)
aluma = DLAPICamera(gw, 'aluma', verbose=True)

aluma.connect()
time.sleep(0.5)

for i in range(10000):
    start = datetime.now()
    aluma.expose(0.1,'light', checksum=True, debug=True, filename="/tmp/tmp.fits")
    end = datetime.now()
    elapsed = (end - start)/timedelta(seconds=1)
    print(f"Image {i}. Time: {elapsed}s. Checksum: {aluma._checksum}")