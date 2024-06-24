# SNR - Signal-to-noise ratio calculations relevant to astronomical imaging

## Modules

### improc - basic image processing tools

### background - sky background modeling tools

### skyrender - artificial image creation tools


## Examples

```
from dcp.dragonfly import utility

# Display the header for a single file
utility.header("data/2024-06-03/AL694M-21061001_1_light.fits")

# Summarize headers for all FITS files in a directory
utility.summarize_directory("data/2024-06-03", 
    keys=['DATE', 'EXPTIME', 'FWHM', 'FOCUSPOS', 'CCD-TEMP', 'NAXIS1', 'NAXIS2','IMAGETYP'])

# Select a range of frames
utility.summarize_directory(
    "data/2024-06-03", 
    keys=['DATE', 'EXPTIME', 'FWHM', 'FOCUSPOS', 'CCD-TEMP', 'NAXIS1', 'NAXIS2','IMAGETYP'], 
    start=10, end=20)

# `summarize_directory()` returns a data frame so it can be stored in a variable. 
df = utility.summarize_directory(
    "data/2024-06-03", 
    keys=['DATE', 'EXPTIME', 'FWHM', 'FOCUSPOS', 'CCD-TEMP', 'NAXIS1', 'NAXIS2','IMAGETYP'])

# Summarize just the darks
df[df['IMAGETYP'] == 'dark']

# Summarize the 'good' (FWHM < 2.5) frames.
df[(df['IMAGETYP'] == 'light') & (df['FWHM'] < 2.5)]

# Get the FWHM values
df['FWHM'].to_list()
```