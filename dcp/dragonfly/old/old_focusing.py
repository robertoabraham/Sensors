import logging
from matplotlib import pyplot as plt

from dragonfly import utility as utility
from dragonfly import improc as improc
from dragonfly import graphics as graphics
from dragonfly import dcp as dcp
from dragonfly import state as state

log = logging.getLogger('team_dragonfly')
log.addHandler(logging.NullHandler())

# If you want to see information messages in iPython interactive sessions:
# import logging
# log = logging.getLogger('team_dragonfly')
# log.setLevel(logging.INFO)

def analyze_focus_run(directory, start=1, end=1000000, verbose=True, plot=True,
                      min_area=3, detection_sigma=2):
    """analyze_focus_run - return a DataFrame recording image quality for a set of images.

    Args:
        directory (string): directory holding a set of FITS images.
        start (int, optional): image number to start analysis. Defaults to 1.
        end (int, optional): image number to end analysis. Defaults to 1000000.
        verbose (bool, optional): print information as analysis proceeds. Defaults to True.
        plot (bool, optional): show a basic plot on the console. Defaults to True.
        min_area (int, optional): minimum area to segment on the image. Defaults to 3.
        detection_sigma (int, optional): number of sigma above sky to threshold image. Defaults to 2.

    Returns:
        _type_: _description_
    """
    df = utility.summarize_directory(directory, start, end, full_path = True)
    files = df['FILENAME'].to_list()
    fwhm_list = []
    nobj_list = []
    sky_list = []
    for file in files:
        try:
            if (verbose):
                print("Analyzing: {}".format(file))
            info = improc.analyze_image(file, detection_sigma = detection_sigma, 
                                        min_area = min_area)
            (fwhm, fwhmrms, nobj, sky, skyrms) = info
            fwhm_list.append(fwhm)
            nobj_list.append(nobj)
            sky_list.append(sky)
            if (verbose):
                print("FWHM: {}  SKY: {}  NOBJ: {}".format(fwhm, sky, nobj))
        except:
            fwhm_list.append(None)
            nobj_list.append(None)
            sky_list.append(None)
    df['FWHM'] = fwhm_list
    df['NOBJ'] = nobj_list
    df['SKY'] = sky_list
    
    if plot:
        plot_focus_run(df)
        
    return df

def plot_focus_run(df, plotfile = '/tmp/analyze_focus_run.png'):
    """plot_focus_run - makes a simple plot from a dataframe

    Args:
        df (DataFrame): dataframe of focus run generated by analyze_focus_run()
        plotfile (str, optional): PNG filename. Defaults to '/tmp/analyze_focus_run.png'.
    """
    df.plot(x='FOCUSPOS', y='FWHM', figsize=(4, 4))
    plt.savefig(plotfile, format='png', dpi=300)
    graphics.show_png(plotfile)   
    
def set_and_check(focusval, exptime=0.1, camera="aluma", 
                  zoom=False, zoom_box_size=[200,200], 
                  zoom_box_position=[1500,500]):
    """set_and_check - sets focus to a position and displays image

    Args:
        focusval (int): setpoint for Canon lens focuser
        exptime (float, optional): expoosure time in seconds. Defaults to 0.1.
        camera (str, optional): name of camera server. Defaults to "aluma".
    """
    dcp.send("fastlens", "goto", "z", focusval)
    dcp.send(camera, "set", "exptime", exptime)
    dcp.send(camera, "expose")
    filename = state.get_state_variable(camera, 'last_filename')
    graphics.create_png(filename, show=True, zoom=zoom, 
                        zoom_box_size=zoom_box_size, 
                        zoom_box_position=zoom_box_position)
       