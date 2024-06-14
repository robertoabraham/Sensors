import time
import threading
import signal
import sys
import math
import json
import os
import numpy as np

import astroalign as aa

from astropy.io import fits

from dragonfly.time_series import TimeSeries
from dragonfly.log import DFLog
from dragonfly.hardware.diffraction_limited.camera import DLAPICamera
from dragonfly.hardware.canon import CanonEFLens
from dragonfly.utility import display_png

class ActiveOpticsGuiderError(Exception):
    """Exception raised when the a guide error occurs."

    Attributes:
        message - error message
    """

    def __init__(self, message:str = "ActiveOpticsGuider error.", custom_field:str = '[ActiveOpticsGuider]'):
        self. message = message
        self.logger = DFLog('ActiveOpticsGuider').logger
            
        self.logger.error(self.message)
        super().__init__(self.message)
    pass


class ActiveOpticsGuider(object):
    """ActiveOpticsGuider - CanonEFLens and DLAPICamera come together to autoguide.
    """
    
    def __init__(self, starchaser:DLAPICamera, lens:CanonEFLens, verbose:bool=False):
        """Initializes the PegasusPowerbox object.
        """
        self.camera = starchaser
        self.lens = lens
        self.verbose = verbose
        self.time_series = TimeSeries()
        
        self.calibration_file="/tmp/is_calibration.json"
            
        self._state = {}
        self._state['is_connected'] = False
        self._state['is_calibrated'] = False
        self._state['is_guiding'] = False
        self._state['exposure_time'] = 15
        self._state['guiding_interval'] = 30
        self._state['binning'] = 1
        self._state['reference_image'] = None
        
        # Polling
        self._guiding_thread = None
        self._guiding_enabled = False
        self._stop_guiding = threading.Event()
        self._activity_lock = threading.Lock()
        
        # Add signal handler for SIGINT signal
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Add custom logger
        self.logger = DFLog("ActiveOpticsGuider").logger


    @property
    def state(self):
        return self._state
    
    def __del__(self):
        self.logger.info("ActiveOpticsGuider deallocated.")

    def _signal_handler(self, sig, frame):
        """Signal handler for SIGINT signal."""
        self.stop_guiding()  # This also shuts down the polling thread.
        sys.exit(0)

    def _execute_guide_iteration(self):
        """Function that is executed periodically in a thread to guide."""
        while not self._stop_guiding.is_set():
            self.take_image_and_align_to_reference_image()
            time.sleep(self._state['guiding_interval'])
            if self._stop_guiding.is_set():
                break
            
    def check_connected(self):
        """Checks if the guider components are connected.

        Raises:
            DLAPICameraError: Error that occurs when the guider components could not be connected.
        """
        if not self._state['is_connected']:
            raise ActiveOpticsGuiderError("Error. Could not connect to guider components.")

    def set_guiding_interval(self, seconds):
        """Sets the time between guider corrections.

        Args:
            seconds (int): Polling interval in seconds.
        """
        self.logger.info(f"Setting the guiding interval to {seconds} seconds.")
        self._state['guiding_interval'] = seconds
        
    def set_exposure_time(self, seconds):
        """Sets the exposure time on the guide camera.

        Args:
            seconds (int): Exposure time in seconds.
        """
        self.logger.info(f"Setting the exposure time to {seconds} seconds.")
        self._state['exposure_time'] = seconds
        
    def clear_reference_image(self):
        self._state['reference_image'] = None
               
    def get_status(self):
        """Get general status of the active optics guiding system.

        Returns:
            state (dict): General status of the camera.
        """
        self.logger.info(f"Active optics guider status: {self._state}")
        return self._state
    
    def reset(self):
        self.stop_guiding()
        self.time_series.clear()
        self._state['reference_image'] = None

    def connect(self):
        """Connects to the active optics systm.

        Raises:
            ActiveOpticsGuiderError: Error raised if the guiding system cannot be connected to.

        Returns:
            string: Returns the string "Active optics system connected." if successful.
        """
        try:
            if self.camera.state['is_connected'] == False:
                print("Connecting to camera...")
                self.camera.connect()
            if self.lens.state['is_connected'] == False:
                print("Connecting to lens...")
                self.lens.connect()
            self._state['is_connected'] = True
            if not os.path.exists(self.calibration_file):
                self._state['is_calibrated'] = False
            else:
                self._state['is_calibrated'] = True

            self.logger.info("Active optics system connected.")
        except:
            raise ActiveOpticsGuiderError(f"Could not connect to active optics system.")

    def disconnect(self):
        """Disconnects from the active optics system.

        Returns:
            string: Returns the string "Active optics system disconnected." if successful.
        """
        self.stop_guiding()
        self.state['is_connected'] = False
        self.logger.info("Disconnected from the guider")
        return "Active optics system disconnected."
        
    def start_guiding(self):
        """Run guide commands periodically."""
        if not self._guiding_enabled:
            # Take initial reference image.
            self.logger.info("Taking reference image.")
            self.camera.expose(self._state['exposure_time'], "light")
            self._guiding_enabled = True
            self._stop_guiding.clear()
            # Start the guiding thread.
            self.logger.info("Starting the guiding thread.")
            self._guiding_thread = threading.Thread(target=self._execute_guide_iteration, daemon=True)
            self._guiding_thread.start()
            self._state['is_guiding'] = True
            self.logger.info("Guiding started.")

    def stop_guiding(self):
        """Stops polling the get_status() method."""
        if self._guiding_enabled:
            self.logger.info("Stopping the guiding thread.")
            self._stop_guiding.set()
            self._guiding_thread.join()
            self._guiding_enabled = False
            self._state['is_guiding'] = False
            self.logger.info("Guiding stopped.")
            
    def display(self):
        """Display the current guiding plot."""
        display_png("/tmp/guiding.png")
            
    def trim_guider_image(self, input_filename, output_filename):
        "Extract the illuminated portion of a DF-Starchaser guider image"
        try:
            if self.verbose:
                self.logger.info('Loading guider image.') 
            hdu = fits.open(input_filename)[0]
            data, h_original = hdu.data, hdu.header

            nx = h_original['NAXIS1']
            ny = h_original['NAXIS2']
            self.logger.info('Read in {} x {} image'.format(nx,ny))

            # Trim the bottom portion
            if self.verbose:
                self.logger.info('Trimming guider image.') 
            start_y = 1
            end_y = int(0.5*ny)
            new_data = data[start_y:end_y,:]
            new_ny = end_y - start_y

            # Put the trimmed data in the HDU
            if self.verbose:
                self.logger.info('Saving trimmed guider image to {}'.format(output_filename)) 
            hdu.data = new_data
            hdu.header['NAXIS2'] = new_ny
            hdu.header['HISTORY'] = 'Trimmed to extract illuminated portion of guider image.'

            # Save the new file
            hdu.writeto(output_filename, overwrite=True)

        except:
            self.logger.error('Could not trim the guider image.')
            raise ActiveOpticsGuiderError("Could not trim the guider image.")
        
        
    def create_difference_image(self, image1, image2, output_filename, verbose=False):
        "Create a difference image"
        try:
            if verbose:
                print(f"Opening {image1}")
            hdul = fits.open(image1)
            data1 = hdul[0].data
            hdul.close()
            data1 = np.float32(data1)

            if verbose:
                print(f"Opening {image2}")
            hdul = fits.open(image2)
            data2 = hdul[0].data
            hdul.close()
            data2 = np.float32(data2)
            
            if verbose:
                print(f"Creating difference image.")
            new_data = data2 - data1

            # Save the new file
            if verbose:
                print(f"Saving difference image as: {output_filename}")
            hdu = fits.PrimaryHDU(data=new_data)
            hdu.writeto(output_filename, overwrite=True)

        except:
            self.logger.error('Could not create difference image.')
            raise ActiveOpticsGuiderError("Could not create difference image.")

    def similarity_transform(self, file1, file2):
        """
        Determine the transformation matrix to map one image to another.

        See also: 

        https://scikit-image.org/docs/dev/api/skimage.transform.html#skimage.transform.SimilarityTransform

        """

        # Trim the images to extract the illuminated portions. 
        trimmed_file1 = '/tmp/im1.fits'
        trimmed_file2 = '/tmp/im2.fits'
        im1 = self.trim_guider_image(file1, trimmed_file1)
        im2 = self.trim_guider_image(file2, trimmed_file2)

        # Get the image data as numpy arrays
        hdu1 = fits.open(trimmed_file1)[0]
        hdu2 = fits.open(trimmed_file2)[0]
        data1 = hdu1.data
        data2 = hdu2.data

        # Compute the similarity matrix
        transformation, (source_list, target_list) = aa.find_transform(data1, data2)
        
        # QC checks
        if (not math.fabs(transformation.scale - 1.0) < 0.01):
            raise ActiveOpticsGuiderError("Scale factor not close to 1.0.")
        if (not math.fabs(transformation.rotation) < 0.01):
            raise ActiveOpticsGuiderError("Rotation factor not close to 0.0.")

        # All is OK - return the transformation
        return transformation

    def take_image_and_align_to_reference_image(self):
        """
        Takes an exposure and shifts the IS lens so the new image matches the reference image.
        """
        
        self.logger.info("Initiating active optics correction.")
        
        if self._state['is_calibrated'] == False:
            self.logger.error("Error. Active optics system is not calibrated.")
            raise ActiveOpticsGuiderError("Cannot guide. Active optics system is not calibrated.")

        # Load calibration file and define matrix elements
        with open(self.calibration_file) as json_file:
            json_data = json.load(json_file)
        b11 = float(json_data["B11"])
        b12 = float(json_data["B12"])
        b21 = float(json_data["B21"])
        b22 = float(json_data["B22"])
        
        # Define the reference image
        if self._state['reference_image'] == None:
            self.logger.info("Reference image not defined! Using last image taken as reference.")
            reference_image = self.camera.latest_image
            self._state['reference_image'] = reference_image
        else:
            reference_image = self._state['reference_image']    
        if reference_image is None or not os.path.exists(reference_image):
            raise ActiveOpticsGuiderError(f"Could not find reference image.")

        if self.verbose:
            self.logger.info("Reference image: {}".format(reference_image))

        # Take a new image
        if self.verbose:
            self.logger.info("Taking exposure.")
        self.camera.expose(self._state['exposure_time'], "light")
        new_image = self.camera.latest_image
        
        # Create difference image
        self.create_difference_image(reference_image, new_image, "/tmp/before.fits")

        # Figure out translation needed to match new image to reference image
        if self.verbose:
            self.logger.info("Computing similarity transformation matrix")
        sm1 = self.similarity_transform(new_image,reference_image)
        dx = sm1.translation[0]
        dy = sm1.translation[1]
        if self.verbose:
            self.logger.info("Image shift relative to to reference image: ({},{})".format(dx,dy))
        dx_is = int(b11*dx + b12*dy)
        dy_is = int(b21*dx + b22*dy)
        if self.verbose:
            self.logger.info("Corresponding IS shift to register images: ({},{})".format(dx_is,dy_is))

        # Move the IS unit.
        if self.verbose:
            self.logger.info("Getting current IS unit position") 
        pos = self.lens.get_is_position()
        current_x = pos[0]
        current_y = pos[1]
        if self.verbose:
            self.logger.info("IS currently at ({},{})".format(current_x, current_y))
        want_x = current_x + dx_is
        want_y = current_y + dy_is
        self.logger.info("Translating IS unit in X direction by {} digital units to go to {}.".format(dx_is,want_x))
        self.lens.set_is_x_position(want_x)
        self.logger.info("Translating IS unit in Y direction by {} digital units to go to {}.".format(dy_is,want_y))
        self.lens.set_is_y_position(want_y)
        self.logger.info("Image shift completed.")
        
        # Create the check image.
        if self.verbose:
            self.logger.info("Taking verification exposure.")
        self.camera.expose(self._state['exposure_time'], "light")
        new_image = self.camera.latest_image
        
        # Create a difference image showing the new image relative to the reference image.
        self.create_difference_image(reference_image, new_image, "/tmp/after.fits")
        
        # Record this movement for posterity
        self.time_series.add_point(dx, dy)
        self.logger.info("Image alignment completed.")
        
    def calibrate(self, shift=50):
        """
        calibrate_guider - calibrate Canon lens IS unit.

        This script determines the constants needed to map from IS digital units to
        pixels on the guide camera.
        """

        tmpfile1 = '/tmp/is_calibration_run_position_1.fits'
        tmpfile2 = '/tmp/is_calibration_run_position_2.fits'
        results_file = '/tmp/is_calibration.json'
        results = {}

        self.logger.info("Starting Image Stabilization Unit calibration run.")

        # Unlock IS unit
        self.logger.info("Unlocking the Image Stabilization unit")
        self.lens.activate_image_stabilization()
    
        # STEP 1 - Calibrate X-axis  
        self.logger.info("Calibrating X-axis on the Image Stabilization Unit.")

        # Move IS unit to position (0,0)
        self.logger.info("Homing the IS unit.")
        self.lens.set_is_x_position(0)
        self.lens.set_is_y_position(0)

        # Print IS position
        pos = self.lens.get_is_position()
        self.logger.info("IS position currently set to: {}".format(pos))

        # Take first short exposure (/tmp/position_0_0_a.fits) 
        self.logger.info("Taking exposure.")
        self.camera.expose(self._state['exposure_time'], "light", filename=tmpfile1)

        # Shift IS unit by shift units in X direction
        self.logger.info("Shifting IS unit by {} units in X-direction.".format(shift))
        self.lens.set_is_x_position(shift)

        # Print IS position
        pos = self.lens.get_is_position()
        self.logger.info("IS position currently set to: {}".format(pos))
    
        # Take second short exposure (/tmp/position_10_0.fits)
        self.logger.info("Taking exposure.")
        self.camera.expose(self._state['exposure_time'],"light", filename=tmpfile2)

        # Solve for X-axis motion terms.
        self.logger.info("Computing similarity transformation matrix.")
        sm1 = self.similarity_transform(tmpfile1, tmpfile2)
        self.logger.info("Translation: {}".format(sm1.translation))
        self.logger.info("Rotation: {}".format(sm1.rotation))
        self.logger.info("Scale: {}".format(sm1.scale))
        a11 = sm1.translation[0]/shift
        a12 = sm1.translation[1]/shift

        # STEP 2 - Calibrate X-axis  
        self.logger.info("Calibrating Y-axis on the Image Stabilization Unit.")

        # Move IS unit to position (0,0)
        self.logger.info("Homing the IS unit.")
        self.lens.set_is_x_position(0)
        self.lens.set_is_y_position(0)

        # Print IS position
        pos = self.lens.get_is_position()
        self.logger.info("IS position currently set to: {}".format(pos))

        # Take first short exposure (/tmp/position_0_0_a.fits) 
        self.logger.info("Taking exposure.")
        self.camera.expose(self._state['exposure_time'], "light", filename=tmpfile1)

        # Shift IS unit by shift units in Y direction
        self.logger.info("Shifting IS unit by {} units in Y-direction.".format(shift))
        self.lens.set_is_y_position(shift)

        # Print IS position
        pos = self.lens.get_is_position()
        self.logger.info("IS position currently set to: {}".format(pos))
    
        # Take second short exposure (/tmp/position_10_0.fits)
        self.logger.info("Taking exposure.")
        self.camera.expose(self._state['exposure_time'], "light", filename=tmpfile2)

        # Solve for Y-axis motion terms.
        self.logger.info("Computing similarity transformation matrix.")
        sm1 = self.similarity_transform(tmpfile1, tmpfile2)
        self.logger.info("Translation: {}".format(sm1.translation))
        self.logger.info("Rotation: {}".format(sm1.rotation))
        self.logger.info("Scale: {}".format(sm1.scale))
        a21 = sm1.translation[0]/shift
        a22 = sm1.translation[1]/shift

        self.logger.info("Matrix form solution for X-Y motion found.")
        self.logger.info("A11: {}".format(a11))
        self.logger.info("A12: {}".format(a12))
        self.logger.info("A21: {}".format(a21))
        self.logger.info("A22: {}".format(a22))

        # Save results
        A = [[a11,a12],[a21,a22]]
        B = self.get2x2MatrixInverse(A)
        results["A11"] = A[0][0]
        results["A12"] = A[0][1]
        results["A21"] = A[1][0]
        results["A22"] = A[1][1]
        results["B11"] = B[0][0]
        results["B12"] = B[0][1]
        results["B21"] = B[1][0]
        results["B22"] = B[1][1]
        with open(results_file, 'w', encoding='utf8') as fp:
            json.dump(results, fp, indent=4)

        # Move IS unit to position (0,0)
        self.logger.info("Homing the IS unit.")
        self.lens.set_is_x_position(0)
        self.lens.set_is_y_position(0)

        # Print IS position
        pos = self.lens.get_is_position()
        self.logger.info("IS position currently set to: {}".format(pos))

        # Save calibration data to state directory state/calibration.json
        self.logger.info("Calibration run completed. Results saved in {}.".format(results_file))
        self._state['is_calibrated'] == True
        print("Calibration run completed.")
            
    def get2x2MatrixDeternminant(self, m):
        if len(m) != 2:
            raise ValueError
        return m[0][0]*m[1][1]-m[0][1]*m[1][0]

    def get2x2MatrixInverse(self, m):
        if len(m) != 2:
            raise ValueError
        determinant = self.get2x2MatrixDeternminant(m)
        return [[m[1][1]/determinant, -1*m[0][1]/determinant], [-1*m[1][0]/determinant, m[0][0]/determinant]]
