#!/home/dragonfly/miniforge3/envs/active_optics/bin/python

import time
import argparse

from dragonfly import camera
from dragonfly import improc


def main():
    parser = argparse.ArgumentParser(
                    prog='continuous_display',
                    description='Takes an image with a camera and displays it',
                    epilog='Copyright Team Dragonfly')

    parser.add_argument("exptime", type=float, help="exposure time")
    parser.add_argument("-c", "--camera", type=int, choices=[0, 1],
                        default=0, help="camera number (default = 0)")
    parser.add_argument("-v", "--verbose", default=False, action="store_true",
                        help="increase output verbosity (default=False")
    parser.add_argument("-o", "--overscan", default=False, action="store_true",
                        help="include overscan (default=False)")
    parser.add_argument("-k", "--keep_images", default=False,
                        action="store_true",
                        help="keep images (default=False)")
    parser.add_argument("-l", "--lower", default=3, type=float,
                        help="number of sigma below sky (default=3)")
    parser.add_argument("-u", "--upper", default=10, type=float,
                        help="number of sigma above sky (default=10)")
    parser.add_argument("-t", "--transformation", default="sqrt", type=str,
                        help="screen transfer function (default=sqrt)")
    parser.add_argument("-s", "--subtract_background", default=False,
                        action="store_true",
                        help="subtract a 2D background model (default=False)")

    args = parser.parse_args()

    camnum = args.camera
    exptime = args.exptime
    include_overscan = args.overscan
    keep_images = args.keep_images
    lower = args.lower
    upper = args.upper
    transformation = args.transformation
    subtract_background = args.subtract_background

    camera_string = str(int(camnum))
    exptime_string = str(exptime)
    max_readout_time = 7
    wait_time = 0.1

    i_iteration = 0

    try:
        while True:
            i_iteration = i_iteration + 1
            start = time.time()
            print(f"Exposing for {exptime} seconds")
            camera.expose(camnum, exptime, "light", "/tmp/foobar.fits")
            improc.ds9("/tmp/foobar.fits")

    except KeyboardInterrupt:
        print()
        print("Interrupted")
        end = time.time()
        duration = end - start
        if end > start:
            if (duration < (exptime + max_readout_time)):
                wait_time_for_exposure = exptime + max_readout_time - duration
                print("We are {:.2f} sec into the exposure. ".format(duration),
                      end="")
                print("Waiting {:.2f} seconds before ending.".format(wait_time_for_exposure))
                if (wait_time_for_exposure > 0):
                    time.sleep(wait_time_for_exposure)


if __name__ == "__main__":
    main()
