import subprocess
import threading

from dragonfly.hardware.diffraction_limited.gateway import DLAPIGateway
from dragonfly.hardware.diffraction_limited.camera import DLAPICamera
from dragonfly.hardware.canon import CanonEFLens
from dragonfly.hardware.guider import ActiveOpticsGuider

def setup_dragonfly():
    """Sets up a working dragonfly system

    Returns:
        Array of 'live' dragonfly objects: [starchaser, aluma, lens]
    """
    print("Instantiating objects.")
    gw = DLAPIGateway(verbose=True)
    sc = DLAPICamera(gw, 'starchaser', verbose=True)
    aluma = DLAPICamera(gw, 'aluma', verbose=True)
    lens = CanonEFLens()
    guider = ActiveOpticsGuider(sc, lens, verbose=True)
    print("Connecting to cameras.")
    sc.connect()
    aluma.connect()
    print("Connecting to lens.")
    lens.connect()
    print("Connecting guider.")
    guider.connect()
    return gw, sc, aluma, lens, guider

def ds9(input_filename, zoom="to fit", pan=None, zrange=None, ztrans=None, verbose=False):
    """Displays an image in SAOImage DS9.

    Args:
        input_filename (string): path to FITS file.
        zoom (str|number, optional): Zoom factor to apply to current zoom factor. Defaults to "to fit".
        pan (list, optional): [x,y] position to center in the display. Defaults to None (unchanged).
        zrange (list, optional): [zmin, zmax] display range. Defaults to None (unchanged).
        ztrans (_type_, optional): One of "linear", "sqrt", "log" or None (unchanged). Defaults to None.
        verbose (bool, optional): Display verbose messages. Defaults to False.
    """
    run_xpa_command("file {}".format(input_filename), verbose=verbose)
    if zoom:
        run_xpa_command(f"zoom {zoom}", verbose=verbose)      
    if zrange:
        run_xpa_command(f"scale limits {zrange[0]} {zrange[1]}", verbose=verbose)
    if ztrans:
        run_xpa_command(f"scale {ztrans}", verbose=verbose)
    if pan:
        run_xpa_command(f"pan to {pan[0]} {pan[1]} physical", verbose=verbose)

def run_xpa_command(command, verbose=False):
    """XPA command to be sent to SAOImage DS9.

    Args:
        command (string): XPA command to send.
        verbose (bool, optional): Prints full xpaset command line. Defaults to False.

    Returns:
        Result from the subrocess command that calls xpaset.
    """
    command_line = "/usr/bin/xpaset -p ds9 "
    command_list = command_line.split()
    command_list.append(command)
    if verbose:
        print("Running: {}".format(command_line + " '" + command + "'"))
    result = subprocess.run(command_list, capture_output=True, check=True)
    return result

def focus_viewer(camera, lens, focusval, exptime=0.1, pan=None, zrange=None, 
                 ztrans=None, verbose=False):
    """focus_viewer - sets focus to a position and displays image

    Args:
        focusval (int): setpoint for Canon lens focuser
        exptime (float, optional): expoosure time in seconds. Defaults to 0.1.
        camera (str, optional): name of camera server. Defaults to "aluma".
    """
    lens.set_focus_position(focusval)
    camera.expose(exptime, "light", filename = "/tmp/tmp.fits")
    ds9(camera.latest_image, pan=pan, zrange=zrange, ztrans=ztrans, verbose=verbose)
 
def interactive_display(camera, exptime=0.1, pan=None, zrange=None, 
                 ztrans=None, verbose=False):

    exit_event = threading.Event()
    
    def input_listener():
        while not exit_event.is_set():
            user_input = input()
            if user_input == '?':
                print("Help string goes here.")
            elif user_input == 'q':
                print("Exiting the display loop.")
                exit_event.set()
    
    listener_thread = threading.Thread(target=input_listener)
    listener_thread.start()
    
    print("Displaying image continuously. Press 'q' and hit [return] to exit.")
    while not exit_event.is_set():
        try:
            camera.expose(exptime, "light", filename = "/tmp/tmp.fits")
            ds9(camera.latest_image, pan=pan, zrange=zrange, ztrans=ztrans, verbose=verbose)
        except KeyboardInterrupt:
            print("\nExiting the display loop.")
            break
    
    exit_event.set()
    listener_thread.join()