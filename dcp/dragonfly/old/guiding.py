
import logging
import math
import json
import astroalign as aa
from astropy.io import fits
from dragonfly import lens as lens
from dragonfly import camera as camera 
from dragonfly import utility as utility

# Todo
# Fix inconsistent X-Y, Image... image... (see log)
# Fix inconstent matrix indexing A11 vs A[0][0] etc. 
# Inconsistent doc string titles.

log = logging.getLogger('team_dragonfly')
log.addHandler(logging.NullHandler())

# If you want to see information messages in iPython interactive sessions:
# import logging
# log = logging.getLogger('team_dragonfly')
# log.handlers =[ logging.FileHandler("dashboard/log.txt"), logging.StreamHandler() ]
# log.setLevel(logging.INFO)

class GuiderFileException(Exception):
    "Thrown when an anomaly exists in a guider image file."
    pass

class GuiderDataException(Exception):
    "Thrown when an attempt to manipulate guider data fails."
    pass

class GuiderLensCommunicationException(Exception):
    "Thrown when an attempt to communicate with the lens fails."
    pass

class GuiderTransformationMatrixException(Exception):
    "Thrown when no image match solution can be found."
    pass

def check_guider_file(filename):
    "Determine if a file is a DF-Starchaser guider image."
    if not os.path.isfile(filename):
        raise GuiderFileException
    if not filename.lower().endswith(('.fits','.fit')):
        raise GuiderFileException
    if not "SCP31300M" in filename:
        raise GuiderFileException

def trim_guider_image(input_filename, output_filename):
    "Extract the illuminated portion of a DF-Starchaser guider image"
    try:
        log.info('Loading guider image.') 
        hdu = fits.open(input_filename)[0]
        data, h_original = hdu.data, hdu.header

        nx = h_original['NAXIS1']
        ny = h_original['NAXIS2']
        log.info('Read in {} x {} image'.format(nx,ny))

        # Trim the bottom portion
        log.info('Trimming guider image.') 
        start_y = 1
        end_y = int(0.5*ny)
        new_data = data[start_y:end_y,:]
        new_ny = end_y - start_y

        # Put the trimmed data in the HDU
        log.info('Saving trimmed guider image to {}'.format(output_filename)) 
        hdu.data = new_data
        hdu.header['NAXIS2'] = new_ny
        hdu.header['HISTORY'] = 'Trimmed to extract illuminated portion of guider image.'

        # Save the new file
        hdu.writeto(output_filename, overwrite=True)

    except:
        log.error('Could not trim the guider image.') 

def similarity_transform(file1, file2):
    """
    Determine the transformation matrix to map one image to another.

    See also: 

    https://scikit-image.org/docs/dev/api/skimage.transform.html#skimage.transform.SimilarityTransform

    """

    # Trim the images to extract the illuminated portions. 
    trimmed_file1 = '/tmp/im1.fits'
    trimmed_file2 = '/tmp/im2.fits'
    im1 = trim_guider_image(file1, trimmed_file1)
    im2 = trim_guider_image(file2, trimmed_file2)

    # Get the image data as numpy arrays
    hdu1 = fits.open(trimmed_file1)[0]
    hdu2 = fits.open(trimmed_file2)[0]
    data1 = hdu1.data
    data2 = hdu2.data

    # Compute the similarity matrix
    transformation, (source_list, target_list) = aa.find_transform(data1, data2)
    
    # QC checks
    if (not math.fabs(transformation.scale - 1.0) < 0.01):
        raise GuiderTransformationMatrixException
    if (not math.fabs(transformation.rotation) < 0.01):
        raise GuiderTransformationMatrixException

    # All is OK - return the transformation
    return transformation


def fix_image_shift(exptime, reference_image, 
                    calibration_file="/home/dragonfly/dragonfly-arm/active_optics/state/is_calibration.json",
                    guider_camera_number=0):
    """
    Takes a guider image and moves the IS so the next image matches the reference image.
    """

    # Load calibration file and define matrix elements
    with open(calibration_file) as json_file:
        json_data = json.load(json_file)
    b11 = float(json_data["B11"])
    b12 = float(json_data["B12"])
    b21 = float(json_data["B21"])
    b22 = float(json_data["B22"])

    # Take a new image
    tmpfile1 = '/tmp/latest_guider_image.fits'
    log.info("Taking exposure.")
    camera.expose(guider_camera_number, exptime, tmpfile1)

    # Figure out translation needed to match new image to reference image
    log.info("Computing similarity transformation matrix")
    sm1 = similarity_transform(tmpfile1,reference_image)
    dx = sm1.translation[0]
    dy = sm1.translation[1]
    log.info("Image shift relative to to reference image: ({},{})".format(dx,dy))
    dx_is = -int(b11*dx + b12*dy)
    dy_is = -int(b21*dx + b22*dy)
    log.info("Corresponding IS shift to register images: ({},{})".format(dx_is,dy_is))

    # Move the IS unit.
    log.info("Getting current IS unit position") 
    pos = lens.get_is_position()
    current_x = pos[0]
    current_y = pos[1]
    log.info("IS currently at ({},{})".format(current_x, current_y))
    want_x = current_x + dx_is
    want_y = current_x + dy_is
    log.info("Translating IS unit in X direction by {} digital units to go to {}.".format(dx_is,want_x))
    lens.set_is_x_position(want_x)
    log.info("Translating IS unit in Y direction by {} digital units to go to {}.".format(dy_is,want_y))
    lens.set_is_y_position(want_y)
    log.info("Image shift completed.")

def calibrate_guider(exptime, guider_camera_number=0, shift=50):
    """
    calibrate_guider - calibrate Canon lens IS unit.

    This script determines the constants needed to map from IS unit values to
    pixels on a guide camera.
    """

    tmpfile1 = '/tmp/is_calibration_run_position_1.fits'
    tmpfile2 = '/tmp/is_calibration_run_position_2.fits'
    results_file = '/home/dragonfly/dragonfly-arm/active_optics/state/is_calibration.json'
    results = {}

    log.info("Start of Image Stabilization Unit calibration run.")

    # Check for lens presence
    ok = lens.check_lens_presence()
    if not ok:
        log.error("Lens not found. Calibration run terminated.")
        raise GuiderLensCommunicationException

    # Unlock IS unit
    log.info("Unlock the Image Stabilization unit")
    lens.activate_image_stabilization()

 
    # STEP 1 - Calibrate X-axis  
    log.info("Calibrating X-axis on the Image Stabilization Unit.")

    # Move IS unit to position (0,0)
    log.info("Homing the IS unit.")
    lens.set_is_x_position(0)
    lens.set_is_y_position(0)

    # Print IS position
    pos = lens.get_is_position()
    log.info("IS position currently set to: {}".format(pos))

     # Take first short exposure (/tmp/position_0_0_a.fits) 
    log.info("Taking exposure.")
    camera.expose(guider_camera_number, exptime, tmpfile1)

    # Shift IS unit by shift units in X direction
    log.info("Shifting IS unit by {} units in X-direction.".format(shift))
    lens.set_is_x_position(shift)

    # Print IS position
    pos = lens.get_is_position()
    log.info("IS position currently set to: {}".format(pos))
   
    # Take second short exposure (/tmp/position_10_0.fits)
    log.info("Taking exposure.")
    camera.expose(guider_camera_number, exptime,tmpfile2)

    # Solve for X-axis motion terms.
    log.info("Computing similarity transformation matrix.")
    sm1 = similarity_transform(tmpfile1, tmpfile2)
    log.info("Translation: {}".format(sm1.translation))
    log.info("Rotation: {}".format(sm1.rotation))
    log.info("Scale: {}".format(sm1.scale))
    a11 = sm1.translation[0]/shift
    a12 = sm1.translation[1]/shift

    # STEP 2 - Calibrate X-axis  
    log.info("Calibrating Y-axis on the Image Stabilization Unit.")

    # Move IS unit to position (0,0)
    log.info("Homing the IS unit.")
    lens.set_is_x_position(0)
    lens.set_is_y_position(0)

    # Print IS position
    pos = lens.get_is_position()
    log.info("IS position currently set to: {}".format(pos))

    # Take first short exposure (/tmp/position_0_0_a.fits) 
    log.info("Taking exposure.")
    camera.expose(guider_camera_number, exptime, tmpfile1)

    # Shift IS unit by shift units in Y direction
    log.info("Shifting IS unit by {} units in Y-direction.".format(shift))
    lens.set_is_y_position(shift)

    # Print IS position
    pos = lens.get_is_position()
    log.info("IS position currently set to: {}".format(pos))
   
    # Take second short exposure (/tmp/position_10_0.fits)
    log.info("Taking exposure.")
    camera.expose(guider_camera_number, exptime,tmpfile2)

    # Solve for Y-axis motion terms.
    log.info("Computing similarity transformation matrix.")
    sm1 = similarity_transform(tmpfile1, tmpfile2)
    log.info("Translation: {}".format(sm1.translation))
    log.info("Rotation: {}".format(sm1.rotation))
    log.info("Scale: {}".format(sm1.scale))
    a21 = sm1.translation[0]/shift
    a22 = sm1.translation[1]/shift

    log.info("Matrix form solution for X-Y motion found.")
    log.info("A11: {}".format(a11))
    log.info("A12: {}".format(a12))
    log.info("A21: {}".format(a21))
    log.info("A22: {}".format(a22))

    # Save results
    A = [[a11,a12],[a21,a22]]
    B = utility.get2x2MatrixInverse(A)
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
    log.info("Homing the IS unit.")
    lens.set_is_x_position(0)
    lens.set_is_y_position(0)

    # Print IS position
    pos = lens.get_is_position()
    log.info("IS position currently set to: {}".format(pos))

    # Save calibration data to state directory state/calibration.json
    log.info("Calibration complete. Results saved in {}.".format(results_file))
