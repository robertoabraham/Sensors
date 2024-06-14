import logging
import subprocess
import os
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.nddata import Cutout2D
from astropy.stats import SigmaClip
from astropy.visualization import MinMaxInterval, SqrtStretch, ImageNormalize
from photutils.background import StdBackgroundRMS, ModeEstimatorBackground, Background2D

log = logging.getLogger('team_dragonfly')
log.addHandler(logging.NullHandler())

# If you want to see information messages in iPython interactive sessions:
# import logging
# log = logging.getLogger('team_dragonfly')
# log.setLevel(logging.INFO)

def create_png(input_filename, output_filename="/tmp/create_png.png", 
               lower_nsigma=2, upper_nsigma=10, transformation="sqrt", 
               subtract_background=False, show=False, 
               zoom=False, zoom_box_size=[200,200], zoom_box_position=[1500,500],
               catalog=None):
    """
    create_png - creates a scaled png image from a FITS file.

    """

    log.info("Loading image: %s" %input_filename)
    f = fits.open(input_filename)
    data, h_original = f[0].data, f[0].header
        
    log.info("Computing sky background level and standard deviation.") 
    sigma_clip = SigmaClip(sigma=3.0)
           
    bkg = ModeEstimatorBackground(median_factor=3.0, mean_factor=2.0, sigma_clip=sigma_clip)
    sky = bkg.calc_background(data)
    log.info("sky = {:.3f}".format(sky))
            
    bkgrms = StdBackgroundRMS(sigma_clip)
    skyrms = bkgrms.calc_background_rms(data)
    log.info("rms = {:.3f}".format(skyrms))

    vmin = sky - lower_nsigma*skyrms
    vmax = sky + upper_nsigma*skyrms
    norm = ImageNormalize(vmin=vmin, vmax=vmax, stretch=SqrtStretch())
    
    if subtract_background:
        log.info("Computing background model.")
        bkg_2d = Background2D(data, (30, 30), filter_size=(11, 11), 
            sigma_clip=sigma_clip, bkg_estimator=bkg) 
        log.info("Rendering image.")
        w = 12.0 
        h = 5.0
        fig, (ax1, ax2) = plt.subplots(2, 2)
        fig.set_size_inches(w,h)
        im1 = ax1.imshow(data, cmap='gray', origin='lower', aspect='equal', norm=norm)
        im2 = ax2.imshow(bkg_2d.background, cmap='gray', origin='lower', 
                aspect='equal', norm=norm)
        im3 = ax2.imshow(data - bkg_2d.background, cmap='gray', origin='lower', 
                aspect='equal', norm=norm)
    else:
        log.info("Rendering image.")
        w = 6.5
        h = 5.0
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)
        fig.set_size_inches(w,h)
        plt.title(os.path.basename(input_filename))
        plt.xlabel('X')
        plt.ylabel('Y')
        if zoom:
            data = Cutout2D(data, zoom_box_position, zoom_box_size).data
            query_string = 'xcentroid > {} & xcentroid < {} & ycentroid > {} & ycentroid < {}'.format(
                int(zoom_box_position[0] - zoom_box_size[0]/2),
                int(zoom_box_position[0] + zoom_box_size[0]/2),
                int(zoom_box_position[1] - zoom_box_size[1]/2),
                int(zoom_box_position[1] + zoom_box_size[1]/2)
            )
            catalog = catalog.query(query_string)
            xval = catalog['xcentroid'].values - zoom_box_position[0] + zoom_box_size[0]/2
            yval = catalog['ycentroid'].values - zoom_box_position[1] + zoom_box_size[1]/2
        else:
            xval = catalog['xcentroid'].values
            yval = catalog['ycentroid'].values    
        
        im = ax.imshow(data, cmap='gray', origin='lower', aspect='equal', norm=norm)
        if catalog is not None:
            ax.scatter(x=xval, y=yval, facecolors='none', edgecolors='b')
        fig.colorbar(im)

    # Save the image as a PNG
    log.info("Saving PNG to {}.".format(output_filename))
    plt.savefig(output_filename, dpi=200)
    plt.close()
    
    # Optionally display the image.
    if show:
        show_png(output_filename)

def show_png(png_filename, timeout=5):
    "Display a PNG image using iTerm2"
    imgcat_exe = "/home/dragonfly/dragonfly-arm/active_optics/dcp/imgcat.sh"
    command = ["/usr/bin/bash", imgcat_exe, png_filename]
    try:
        returncode = subprocess.call(command, timeout=timeout)
    except subprocess.TimeoutExpired:
        print('Error. Timed out. Display attempt failed.')

def show(input_filename):
    tmpfile = "/tmp/graphics-show-tmp1.png"
    png = create_png(input_filename,tmpfile)
    show_png(tmpfile)


