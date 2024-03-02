import numpy as np
import subprocess
from astropy.io import fits
from astropy.stats import SigmaClip
from astropy.stats import sigma_clipped_stats
from astropy.visualization import MinMaxInterval, SqrtStretch, ImageNormalize
from astropy.nddata import Cutout2D
from astropy.stats import SigmaClip
import os

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from mpl_toolkits.axes_grid1.inset_locator import (inset_axes, InsetPosition, mark_inset)

from photutils import Background2D
from photutils import detect_sources
from photutils.segmentation import deblend_sources
from photutils.segmentation import SourceCatalog
from photutils.background import StdBackgroundRMS, ModeEstimatorBackground, Background2D
from photutils.centroids import centroid_quadratic
from photutils.profiles import RadialProfile
from photutils.datasets import make_noise_image

from astropy.samp import SAMPIntegratedClient


# import astrometry

import logging
log = logging.getLogger('team_dragonfly')
log.addHandler(logging.NullHandler())

import logging

# Only one client should ever exist, so create it here.
client = SAMPIntegratedClient(addr='127.0.0.1')
client.connect()

# Typical workflow:
#
# # Define the image to study
# import os
# from dragonfly import improc
# datadir = "/home/dragonfly/dragonfly-arm/active_optics/data/bob-focus-run/focus_ha/"
# filename = os.path.join(datadir, 'AL694M-21061402_38_light.fits')
# 
# # Show the whole image
# improc.display(filename)
# 
# # Looks good. Generate a catalog.
# df = improc.create_catalog(filename)
#
# # Overlay the labels on the displayed image.
# improc.display(filename, catalog=df)

# # Zoom in on an interesting region
# improc.display(filename, catalog = df zoom_box_position = [900,200], zoom_box_size=[200,200], zoom=True)
#
# # Display the profiles of a couple of interesting stars
# improc.profile(filename, df, 39)
# improc.profile(filename, df, 30)


def get_fits_header(filename):
    """Returns the header of a FITS file as a dictionary."""
    hdul = fits.open(filename)
    hdr = hdul[0].header
    return hdr


def analyze_sky(filename):
    """ Compute sky estimates

    Args:
        filename (string): Path to a FITS image file.
        
   Returns:
        dict: Dictionary with keywords 'SKY_MEAN', 'SKY_MEDIAN', 'SKY_SIGMA'
    """
    f = fits.open(filename,memmap=False)
    data, hdr = f[0].data, f[0].header
    f.close()
    (sky_mean, sky_median, sky_sigma) = sigma_clipped_stats(data, sigma=2, maxiters=5)  
    image_properties = {}
    image_properties['SKY_MEAN'] = round(sky_mean,3)
    image_properties['SKY_MEDIAN'] = round(sky_median,3)
    image_properties['SKY_SIGMA'] = round(sky_sigma,3)
    return image_properties

def analyze_image(filename, deblend=False, detection_sigma = 2.0, 
                  min_area = 3, verbose=False, store=False):
    """ Computes basic image properties. 

    Args:
        filename (string): Path to a FITS image file.
        show_plot (bool, optional): Displays a diagnostic plot. Defaults to False.
        deblend (bool, optional): De-blends segmentation image. Defaults to False.
        detection_sigma (float, optional): Number of sigma above sky for segmentation. Defaults to 2.0.
        min_area (int, optional): Minimum number of pixels in a segmented object. Defaults to 3.
        verbose (bool, optional): Display diagnostic information. Defaults to False.
        store (bool, optional): Save computed information back into the image header. Defaults to False.

    Returns:
        dict: Dictionary with keywords 'FHWM', 'FHWM_RMS', 'NOBJ', 'SKY_MEAN', 'SKY_MEDIAN', 'SKY_SIGMA'
    """

    # Grab the data
    f = fits.open(filename,memmap=False)
    data, hdr = f[0].data, f[0].header
    f.close()
    
    # Get basic properties
    (sky_mean, sky_median, sky_sigma) = sigma_clipped_stats(data, sigma=2, maxiters=5)   

    df = create_catalog(filename, detection_sigma = detection_sigma, deblend=deblend, 
                        min_area = min_area, verbose=verbose)
    log.info("Determining source properties")
    fwhm = 2.35*np.mean(df['semimajor_sigma'])      
    fwhmrms = 2.35*np.std(df['semimajor_sigma'])
    nobj = len(df['xcentroid'])
    
    # Convert from AstroPy Quantity objects to floats.    
    fwhm = round(fwhm,3)
    fwhmrms = round(fwhmrms,3)   
        
    if store:
        if verbose:
            print("Storing results in the image")
        hdr['FWHM'] = fwhm 
        hdr['FWHMRMS'] = fwhmrms  
        hdr['NOBJ'] = nobj 
        fits.writeto(filename, data, hdr, clobber=True)

    image_properties = {}
    image_properties['FHWM'] = fwhm
    image_properties['FHWM_RMS'] = fwhmrms
    image_properties['NOBJ'] = nobj
    image_properties['SKY_MEAN'] = round(sky_mean,3)
    image_properties['SKY_MEDIAN'] = round(sky_median,3)
    image_properties['SKY_SIGMA'] = round(sky_sigma,3)

    return image_properties


def create_catalog(filename, detection_sigma = 2.0, min_area = 4, verbose=False, 
                   deblend=False):
    """create catalog - create a DataFrame of photometric and morphological properties 
                        for sources on an image.

    Args:
        filename (string): path to FITS image file to be analyzed.
        detection_sigma (float, optional): sky sigma for threshold. Defaults to 2.0.
        min_area (int, optional): minimum area of smallest objects. Defaults to 4.
        verbose (bool, optional): print diagnostic information. Defaults to False.

    Returns:
        DataFrame: catalog as a PANDAS DataFrame.        
    """

    log.info("Reading in {}".format(filename))
    f = fits.open(filename,memmap=False)
    data, hdr = f[0].data, f[0].header
    f.close()
    
    log.info("Computing sky background level and standard deviation.") 
    sigma_clip = SigmaClip(sigma=3.0)

    bkg = ModeEstimatorBackground(median_factor=3.0, mean_factor=2.0, sigma_clip=sigma_clip)
    sky = bkg.calc_background(data)
    log.info("sky = {:.3f}".format(sky))
            
    bkgrms = StdBackgroundRMS(sigma_clip)
    skyrms = bkgrms.calc_background_rms(data)
    log.info("rms = {:.3f}".format(skyrms))
    
    log.info("Subtracting sky model")
    bkg_model = Background2D(data, (30, 30), filter_size=(11, 11), 
            sigma_clip=sigma_clip, bkg_estimator=bkg) 
    data_sub = data - bkg_model.background
    
    log.info("Detecting sources and making segmentation map")
    threshold = detection_sigma * skyrms
    segm = detect_sources(data_sub, threshold, npixels=min_area)

    if deblend:
        log.info("Deblending the segmentation map")
        segm_deblend = deblend_sources(data_sub, segm,
                                npixels=min_area, nlevels=32, contrast=0.001,
                                progress_bar=False)
    else:
        segm_deblend = segm

    log.info("Creating the source catalog")
    cat = SourceCatalog(data_sub, segm_deblend)
    df = cat.to_table().to_pandas()

    return df


def display(input_filename, lower_nsigma=2, upper_nsigma=10, 
            zoom=False, zoom_box_size=[200,200], zoom_box_position=[1000,500],
            catalog=None, label=True):
    """display - displays a FITS file using Matplotlib.

    Args:
        input_filename (string): path to FITS file.
        lower_nsigma (int, optional): number of sky sigma below sky to plot. Defaults to 2.
        upper_nsigma (int, optional): number of sky sigma above sky to plot. Defaults to 10.
        zoom (bool, optional): zoom in a on region of the image. Defaults to False.
        zoom_box_size (list, optional): zoom box size. Defaults to [200,200].
        zoom_box_position (list, optional): position of zoom box centre. Defaults to [1000,500].
        catalog (_type_, optional): PANDAS catalog to use for annotation. Defaults to None.
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

    log.info("Rendering image.")
    w = 6.5
    h = 5.0
    fig = plt.figure()
    #ax = fig.add_subplot(1, 1, 1)
    #fig.set_size_inches(w,h)
    f, ax = plt.subplots(figsize=[w,h])
    plt.title(os.path.basename(input_filename))
    plt.xlabel('X')
    plt.ylabel('Y')
    if zoom:
        zb = zoom_box_size.copy()
        zb.reverse()
        data = Cutout2D(data, zoom_box_position, zb).data
        if catalog is not None:
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
        if catalog is not None:
            xval = catalog['xcentroid'].values
            yval = catalog['ycentroid'].values    

    im = ax.imshow(data, cmap='gray', origin='lower', aspect='equal', norm=norm)
    if catalog is not None:
        ax.scatter(x=xval, y=yval, facecolors='none', edgecolors='b')
        if label:
            labels = catalog['label'].values
            (nx,ny) = data.shape
            extra_space = nx/100
            for i, txt in enumerate(labels):
                ax.annotate(str(txt), (xval[i] + extra_space, yval[i]))
    
    if zoom:
        xoffset = zoom_box_position[0] - zoom_box_size[0]/2
        yoffset = zoom_box_position[1] - zoom_box_size[1]/2
        label_format = '{:,.0f}'
        
        if xoffset < 0:
            xoffset = 0
        if yoffset < 0:
            yoffset = 0
    
        ax.xaxis.set_major_locator(mticker.MaxNLocator(8))
        ticks_loc = ax.get_xticks().tolist()
        ax.xaxis.set_major_locator(mticker.FixedLocator(ticks_loc))
        ax.set_xticklabels([label_format.format(x + xoffset) for x in ticks_loc])
    
        ax.yaxis.set_major_locator(mticker.MaxNLocator(8))
        ticks_loc = ax.get_yticks().tolist()
        ax.yaxis.set_major_locator(mticker.FixedLocator(ticks_loc))
        ax.set_yticklabels([label_format.format(y + yoffset) for y in ticks_loc])
    
    f.colorbar(im)    
    plt.show()
    
    
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
    run_samp_command("file {}".format(input_filename), verbose=verbose)
    if zoom:
        run_samp_command(f"zoom {zoom}", verbose=verbose)      
    if zrange:
        run_samp_command(f"scale limits {zrange[0]} {zrange[1]}", verbose=verbose)
    if ztrans:
        run_samp_command(f"scale {ztrans}", verbose=verbose)
    if pan:
        run_samp_command(f"pan to {pan[0]} {pan[1]} physical", verbose=verbose)


def load_ds9(input_filename, verbose=False):
    """Displays an image into a new ds9 frame.

    Args:
        input_filename (string): path to FITS file.
    """

    params = {}
    params["url"] = f"file://{input_filename}"
    params["name"] = "FITS image to display"
    message = {}
    message["samp.mtype"] = "image.load.fits"
    message["samp.params"] = params
    client.notify_all(message)
    
    
def run_samp_command(command, verbose=False):
    """SAMP command to be sent to SAOImage DS9.

    Args:
        command (string): XPA command to send.
        verbose (bool, optional): Prints full SAMP command. Defaults to False.

    Returns:
        result: result from the samp command
    """
    params = {}
    params["cmd"] = command
    message = {}
    message["samp.mtype"] = "ds9.set"
    message["samp.params"] = params
    result = client.notify_all(message)
    return result


def display_corners(input_filename, lower_nsigma=2, upper_nsigma=10, box = 100):
    """display corners - show images of the corners of a FITS image

    Args:
        input_filename (string): path to FITS image file.
        lower_nsigma (int, optional): number of sky sigma below sky to plot. Defaults to 2.
        upper_nsigma (int, optional): number of sky sigma above sky to plot. Defaults to 10.
        box (int, optional): sub-image box size in pixel to plot. Defaults to 100.
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

    # Cutout the sub-images.
    nx = h_original['NAXIS1']
    ny = h_original['NAXIS2']
    w = box
    h = box
    zb = [w, h]

    ul = [int(w/2), int(ny-h/2)]
    ur = [int(nx - w/2), int(ny - h/2)]
    br = [int(nx - w/2), int(h/2)]
    bl = [int(w/2), int(h/2)]
    
    data_ul = Cutout2D(data, ul, zb).data
    data_ur = Cutout2D(data, ur, zb).data
    data_br = Cutout2D(data, br, zb).data
    data_bl = Cutout2D(data, bl, zb).data
    
    # Render the images
    
    log.info("Rendering sub-images.")
    w = 6.5
    h = 6.5
    
    f, axarr = plt.subplots(2,2)
    f.set_size_inches(w,h)
    f.subplots_adjust(wspace=0, hspace=0)
    axarr[0,0].imshow(data_ul, cmap='gray', origin='lower', aspect='equal', norm=norm)
    axarr[0,1].imshow(data_ur, cmap='gray', origin='lower', aspect='equal', norm=norm)
    axarr[1,0].imshow(data_bl, cmap='gray', origin='lower', aspect='equal', norm=norm)
    axarr[1,1].imshow(data_br, cmap='gray', origin='lower', aspect='equal', norm=norm)
    
    axarr[0,0].axis('off')
    axarr[0,1].axis('off') 
    axarr[1,0].axis('off') 
    axarr[1,1].axis('off') 

    plt.show()
    plt.close(f)
    
    
def plate_solve(catalog, verbose=False, binning=1.0, fast=True, fast_logodds_stop=100):
    """plate_solve - use astrometry.net algorithm to find sky location of a Dragonfly image.

    Args:
        catalog (DataFrame): catalog generated by create_catalog
        verbose (bool, optional): provide detailed solution on plate solve attempt. Defaults to False.
        binning (float, optional): dragonfly camera binning factor. Defaults to 1.0.
        fast (bool, optional): use a quick-and-dirty stopping algorithm. Defaults to True.
        fast_logodds_stop (int, optional): quick-and-dirty log-odds stopping value. Defaults to 50.
        
    Returns:
        dict: a Python dictionary with keywords 'Success', 'CenterRADeg', 'CenterDecDeg', 'ScaleArcsecPerPixel'
        
    Notes:
        If the plate solve is successful, the keyword 'Success' will be True and the keywords 'CenterRADeg',
        'CenterDecDeg', and 'ScaleArcsecPerPixel' will be populated with the solution values. If the plate
        solve is unsuccessful, the keyword 'Success' will be False and the other keywords will be None.
    """
    if verbose:
        logging.getLogger().setLevel(logging.INFO)
    
    stars = catalog[['xcentroid','ycentroid']].values
    
    lower_scale = binning*2.0
    upper_scale = binning*3.0
    solver = astrometry.Solver(
        astrometry.series_5200.index_files(
            cache_directory="astrometry_cache",
            scales={5,6},
        )
        + astrometry.series_4100.index_files(
            cache_directory="astrometry_cache",
            scales={7,8,9,10,11},
        )
    )
    
    if fast:
        # We adopt a solution parameter that returns immediately if
        # logodds > logodds_stop. This non-optimal (the default is to
        # keep going and then rank them) but I figure it's good enough
        # for simple stuff.
        solution = solver.solve(
            stars=stars,
            size_hint=astrometry.SizeHint(
                lower_arcsec_per_pixel=lower_scale,
                upper_arcsec_per_pixel=upper_scale,
            ),
            position_hint=None,
            solution_parameters=astrometry.SolutionParameters(
                logodds_callback=lambda logodds_list: (
                    astrometry.Action.STOP
                    if logodds_list[0] > fast_logodds_stop
                    else astrometry.Action.CONTINUE
                ),
            ),
        )
    else:
        # Use the default solution parameters.
        solution = solver.solve(
            stars=stars,
            size_hint=astrometry.SizeHint(
                lower_arcsec_per_pixel=lower_scale,
                upper_arcsec_per_pixel=upper_scale,
            ),
            position_hint=None,
            solution_parameters=astrometry.SolutionParameters(),
        )       
    
    solution = {}
    if solution.has_match():
        solution['Success'] = True
        solution['CenterRADeg'] = solution.best_match().center_ra_deg
        solution['CenterDecDeg'] = solution.best_match().center_dec_deg
        solution['ScaleArcsecPerPixel'] = solution.best_match().scale_arcsec_per_pixel
    else:
        solution['Success'] = False
        solution['CenterRADeg'] = None
        solution['CenterDecDeg'] = None
        solution['ScaleArcsecPerPixel'] = None
    
    
def display_stamps(input_filename, dataframe, lower_nsigma=2, upper_nsigma=20, 
                   box = 100, ncol = 3): 
    """display stamps - Displays a postage stamp image for each object in a catalog 

    Args:
        input_filename (string): path to FITS image.
        dataframe (DataFrame): catalog of objects generated by create_catalog
        lower_nsigma (int, optional): number of sky sigma below sky for display. Defaults to 2.
        upper_nsigma (int, optional): number of sky sigma above sky for display. Defaults to 10.
        box (int, optional): postage stamp box size in pixels. Defaults to 100.
        ncol (int, optional): number of columms in mosaic. Defaults to 3.
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

    # Figure out the geometry of the situation.
    nstamps = len(dataframe.index)
    nrow = int(nstamps/ncol) + (1 if nstamps % ncol > 0 else 0)

    # Render the images
    f, axarr = plt.subplots(nrow, ncol)
    f.subplots_adjust(wspace=0, hspace=0)
    size_factor = 1.5
    f.set_size_inches(size_factor * ncol, size_factor * nrow)
    count = 0
    zb = [box, box]
    for i in range(nrow):
        for j in range(ncol):
            if count < nstamps:
                xc = dataframe.iloc[count]['xcentroid']
                yc = dataframe.iloc[count]['ycentroid']
                label = dataframe.iloc[count]['label']
                data_stamp = Cutout2D(data, [xc, yc], zb).data
                axarr[i,j].imshow(data_stamp, cmap='gray', origin='lower', aspect='equal', norm=norm)
                plt.text(0.5, 0.9, label, horizontalalignment='center', color='b',
                    verticalalignment='center', transform=axarr[i,j].transAxes)
            axarr[i,j].axis('off')
            count = count + 1
    plt.show()
    plt.close(f)
    

def display_profile(input_filename, catalog, label):
    """display_profile - plots the profile of a star in a catalog

    Args:
        input_filename (string): path to FITS image file.
        catalog (DataFrame): catalog generated by create_catalog().
        label (int): star identified by the value in the catalog's "label" column.

    Returns:
        matplotlib.figure.Figure: a Matplotlib figure object.
    """

    log.info("Getting position of star: %s" %input_filename)
    xc = catalog.query('label=={}'.format(label))['xcentroid'].values[0]
    yc = catalog.query('label=={}'.format(label))['ycentroid'].values[0]

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

    log.info("Computing background model.")
    bkg_2d = Background2D(data, (30, 30), filter_size=(11, 11), 
        sigma_clip=sigma_clip, bkg_estimator=bkg) 
    
    log.info("Subtracting sky background")
    data_sub = data - bkg_2d.background
    xycen = centroid_quadratic(data_sub, xpeak=xc, ypeak=yc)
    edge_radii = np.arange(10)
    
    log.info("Generating a noise field to work out profile errors")
    error = make_noise_image(data_sub.shape, mean=0., stddev=skyrms, seed=123)
    
    rp = RadialProfile(data_sub, xycen, edge_radii, error=error, mask=None)
    # plot the radial profile
    fig, ax1 = plt.subplots()
    rp.plot(label='Radial Profile')
    # ax1.set_yscale('log')
    rp.plot_error()
    plt.plot(rp.radius, rp.gaussian_profile, 
             label='Gaussian Fit (FWHM={} pix)'.format(round(rp.gaussian_fwhm,3)))
    plt.legend()
    
    # Create a set of inset Axes
    ax2 = plt.axes([0,0,1,1])
    ip = InsetPosition(ax1, [0.6,0.5,0.3,0.3])
    ax2.set_axes_locator(ip)
    imdata = Cutout2D(data_sub, [xc,yc], [21,21]).data
    vmin = -3*skyrms
    vmax = rp.profile[0]
    norm = ImageNormalize(vmin=vmin, vmax=vmax, stretch=SqrtStretch())
    ax2.imshow(imdata, cmap='gray', origin='lower', aspect='equal', norm=norm)
    ax2.axis('off')
    
    plt.show()
