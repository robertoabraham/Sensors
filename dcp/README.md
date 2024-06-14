# Software for Controlling Dragonfly Hardware


## Examples

### Example 1 - Verify that key elements of the hardware work

To check individual components, run the test suite.

`pytest -v -s tests`

### Example 2 - Active optics from Bob's basement

This is the 'script' from the active optics demo shown to the team on 2023-10-30. Before playing with it, open up a separate terminal window and set up continuous viewing of the log file:

`tail -f /tmp/dragonfly_log.txt`

The demo from Bob's basement was given by running the commands from an `ipython` shell, but there's no reason it could not have been done from a Jupyter notebook. In any case, if you happen to have a USB microphone available, you can use the `sound_spectrogram.py` script with a gain of about 1000 to verify activity (this clearly identifies cameras turning on and off as fans kick in, lenses focusing and actively stabilizing, mounts slewing, etc).

`./sound_spectrogram.py -g 1000`

Here are the commands that connect to the hardware and start active optics corrections:

```

from dragonfly.hardware.pegasus import PegasusPowerbox
from dragonfly.hardware.astro_physics import GTOControlBox
from dragonfly.hardware.diffraction_limited.gateway import DLAPIGateway
from dragonfly.hardware.diffraction_limited.camera import DLAPICamera
from dragonfly.hardware.canon import CanonEFLens
from dragonfly.hardware.guider import ActiveOpticsGuider
from dragonfly.control import tools
from dragonfly import find
from dragonfly import utility

# Create the objects
pb = PegasusPowerbox(find.find_powerbox_serial_port())
gto = GTOControlBox(find.find_mount_serial_port())
gw = DLAPIGateway(verbose=True)
sc = DLAPICamera(gw, 'starchaser', verbose=True)
aluma = DLAPICamera(gw, 'aluma', verbose=True)
lens = CanonEFLens()
guider = ActiveOpticsGuider(sc, lens, verbose=True)

# Connect the hardware
pb.connect()
gto.connect()
sc.connect()
aluma.connect()
lens.connect()
guider.connect()

# Initialize the lens (this only needs to be done when the lens)
# has been power cycled... and maybe not even that often. In any
# case, this initialization takes quite a while (around 30s) as it
# exercises all lens modes and fully calibrates the lens range.

lens.initialize()

# Focus the starchaser and display an image to make sure everythig is
# more-or-less in focus.

lens.set_focus_position(12901)
sc.expose(0.1, 'light')
tools.ds9(sc.latest_image)

# Write some little routines that jog the mount and then take + display
# an image. These are handy for testing the image stabilization routines.
# Stuff like this probably belongs in the tools module.

def go_north():
    gto.jog('n',0.2)
    sc.expose(0.1, 'light')
    tools.ds9(sc.latest_image)
    
def go_south():
    gto.jog('s',0.2)
    sc.expose(0.1, 'light')
    tools.ds9(sc.latest_image)

# The guider should only need to be calibrated rarely. Maybe once
# a year, if that. But at the moment I stupidly save the calibration
# file as /tmp/is_calibration.json. Everything in /tmp gets
# cleared after a reboot of the Pi, so it is silly to save the
# calibration file file there. But I don't know where to park calibration
# files so they are permanent-ish and easy to access from a 
# container. So, for now, that is where it lives, and you need to
# re-calibrate the guider using its calibrate() method after every 
# reboot of the Raspberry Pi. This only takes a minute or so, 
# so it's not too painful.

if not guider.state['is_calibrated']:
    print("Calibrating the guider.")
    guider.calibrate()

# Set the exposure time and start guiding.

guider.set_exposure_time(0.1)
guider.start_guiding()

# By default the next active optics correction will happen roughly 30s
# after the end of the last correction. You can go way faster if you want
# to. You can watch them occur by monitoring the logfile and/or 
# generating some plots. Here is how to generate the relevant plots. 

utility.display_png('/tmp/guiding.png')
guider.time_series.plot('/tmp/guiding.png')

# To test stuff, periodically use go_north() and go_south() 
# to move the mount by a few arcseconds and watch as the lens
# adapts to fix things. When you are done, and before slewing
# to the next target, be sure to stop guiding!

guider.stop_guiding()

# After a slew, be sure to clear out the old reference image before
# you start guiding on a new target.

guider.clear_reference_image()

# When done, just quit() Python. If you want to, you can first
# disconnect the hardware, though I haven't tested this much. 
# I usually just quit() and let the class destructors manage
# the clean-up for me.

gto.disconnect()
pb.disconnect()
guider.disconnect()
sc.disconnect()
aluma.disconnect()
lens.disconnect()
```

### Example 3 - 'old school' camera control.

The previous example uses the version of the camera control software that controls the cameras from Python by calling directly into recent (v.2.7) version of the DLAPI library. However, existing Raspberry Pi machines in New Mexico are running old versions (v. 1.X) of the DLAPI library, and these cameras are controlled by a C++ command-line program called `dfcore` that links against this old library. Python scripts and programs then use the `subprocess` module to shell out to `dfcore` to control the cameras. This works, but it's slow and clunky. Unfortunately, newer versions of DLAPI require an upgraded version of the Raspberry Pi OS, so we cannot simply upgrade the camera control software without also updating the OS, which is hard to do remotely. 

The correct solution to this problem is to bite the bullet and upgrade the Raspberry Pis to the latest OS and then install the new camera control software. But in the meantime, we have come up with a band-aid solution that layers 'new' camera commands so they work by calling `dfcore` equivalents using the same syntax as the new software. To do this, replace:

```
from dragonfly.hardware.diffraction_limited.gateway import DLAPIGateway
from dragonfly.hardware.diffraction_limited.camera import DLAPICamera

...

gw = DLAPIGateway(verbose=True)
sc = DLAPICamera(gw, 'starchaser', verbose=True)
aluma = DLAPICamera(gw, 'aluma', verbose=True)
```

with:

```
from dragonfly.hardware.diffraction_limited.oldschool_camera import DLAPICamera

...
sc = DLAPICamera('starchaser', verbose=True)
aluma = DLAPICamera('aluma', verbose=True)
```

With these changes, the previous example should still work.
