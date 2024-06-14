import os
from dragonfly import improc
from importlib import reload

datadir = "/home/dragonfly/dragonfly-arm/active_optics/data/bob-focus-run/focus_ha/"
filename = os.path.join(datadir, 'AL694M-21061402_38_light.fits')

improc.display(filename)
df = improc.create_catalog(filename)

improc.display(filename, catalog=df)
improc.display(filename, catalog=df, zoom = True)

improc.display_corners(filename)
bright = df.sort_values("kron_flux",ascending=False).head(10)

improc.display(filename, catalog=bright)
improc.display_stamps(filename, bright, ncol = 5, box=20)

brightest_star_label = bright.iloc[0]['label']
improc.display_profile(filename, bright, brightest_star_label)

# Create a catalog of just the brightest stars and then plate solve the frame. Should take
# less than 30s to plate solve.
df = improc.create_catalog(filename, detection_sigma=4, min_area=4)
improc.plate_solve(df, binning=2)