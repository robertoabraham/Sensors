print("Loading standard modules.")
from importlib import reload
import time
import gc

print("Loading Dragonfly modules.")
from dragonfly.hardware import astro_physics
from dragonfly.hardware import sbig
from dragonfly.hardware import pegasus
from dragonfly.hardware import canon
from dragonfly import improc
from dragonfly import find

print("Instantiating hardware objects.")
gto = astro_physics.GTOControlBox(find.find_mount_serial_port())
pb = pegasus.PegasusPowerbox(find.find_powerbox_serial_port())
aluma = sbig.DLAPICamera("aluma")
sc = sbig.DLAPICamera("starchaser")
#lens = canon.CanonEFLens()

print("Connecting to mount.")
gto.connect()
gto._polling_interval = 5
gto.start_polling()

print("Connecting to powerbox.")
pb.connect()
pb._polling_interval = 5
pb.start_polling()

print("Turning on powerbox.")
pb.quadport_on()

print("Waiting 5s for cameras to come up.")
time.sleep(5)

print("Connecting to cameras.")
aluma.connect()
sc.connect()

#print("Connecting to lens.")
#lens.connect()

#print("Initializing lens.")
#lens.initialize()

#print("Setting lens to approximate focus position.")
#lens.set_focus_position(12660)

#def quick_view(camera, z=lens.state['z'], **kwargs):
#    lens.set_focus_position(z)
#    camera.expose(0.1, "light", wait=True)
#    improc.ds9(camera.last_image, **kwargs)
