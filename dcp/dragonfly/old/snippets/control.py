import threading
import time
import sys
import getch

from dragonfly import improc
from dragonfly import sbig

def my_function(camera):
    if camera.get_status()['IsExposing']:
        return
    else:
        print(f"Taking an image at {time.ctime()}")
        camera.expose(0.1, "light", wait=False)
        improc.ds9(camera.last_image)

def run_until_q_pressed(func, *args, **kwargs):
    """Runs a function over and over until the user presses the 'q' key.

    Args:
        func (function): the function to run
        *args: positional arguments to pass to the function
        **kwargs: keyword arguments to pass to the function
    """
    keep_running = True

    def key_capture_thread():
        nonlocal keep_running
        while keep_running:
            key = getch.getch()
            if key == 'q':
                keep_running = False
                sys.exit()
            if key == 'j':
                print("Doing some j key stuff...")

    def continuous_run():
        nonlocal keep_running
        threading.Thread(target=key_capture_thread, daemon=True).start()
        while keep_running:
            func(*args, **kwargs)
            time.sleep(0.5)

    continuous_run()
    print("Done.")

print("Activating camera.")
sc = sbig.DLAPICamera("starchaser")
sc.connect()
print("Taking and displaying data.")
run_until_q_pressed(my_function, sc)