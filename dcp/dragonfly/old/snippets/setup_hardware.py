from importlib import reload
import gc
import time

from dragonfly import find
from dragonfly.hardware import astro_physics
from dragonfly.hardware import pegasus
from dragonfly.hardware import sbig

pb_port = find.find_powerbox_serial_port()
gto_port = find.find_mount_serial_port()

print("Instantiating powerbox")
pb = pegasus.PegasusPowerbox(pb_port)
print("Connecting to powerbox")
pb.connect()
print("Turning on quadport")
pb.quadport_on()
print("Waiting 5s for powerbox to turn on.")
time.sleep(5)

print("Instantiating mount")
gto = astro_physics.GTOControlBox(gto_port)
print("Connecting to mount.")
gto.connect()
gto._polling_interval = 3
gto.start_polling()

print("Instantiating ALUMA camera")
aluma = sbig.DLAPICamera("aluma")
print("Connecting to ALUMA camera")
aluma.connect()
aluma.get_status()