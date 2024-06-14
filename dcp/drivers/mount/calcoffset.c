#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <termios.h>
#include <slalib.h>

#define R2A 206265.0             /* Radians to arcseconds */
#define PI 3.1415926535897932385 /* Pi to 20 decimal places */


char   *help[] = {
"",
"NAME",
"    calcoffset - calculate new coordinates obtained by adding an offset to a position",
"",
"SYNOPSIS",
"    % calcoffset ra dec dx dy",
"",
"PARAMETERS",
"    ra  - Right ascension in sexagesimal (HH:MM:SS.S) notation",
"    dec - Declination in sexgesimal (sDD*MM:SS.S) notation",
"    dx  - RA offset in arcsec",
"    dy  - Dec offset in arcsec",
"",
"EXAMPLES",
"",
"    % calcoffset 12:33:58.2 -00*15:15.2 5.0 5.5",
"",
"DESCRIPTION",
"",
"    This program computes the coordinates resulting from the addition of an offset",
"    (in arcseconds) to a celestial coordinate specified as HH:MM:SS.S sDD*MM:SS.S.",
"    While this sounds trivial there are a sufficient number of subtleties that the",
"    the SLALIB library is used to do the coordinate conversion. The output can be",
"    passed to other programs (e.g. to slew a telescope to an offset position). The",
"    code is designed to handle pathological cases e.g. offsetting over the pole and ",
"    across the 24h/0h line.",
"",
"AUTHOR",
"    Roberto Abraham (abraham@astro.utoronto.ca)",
"",
"LAST UPDATE",
"    May 2012",
0};


int main (int argc, char *argv[] ) {

    const char delims[]=":*d";
    char ra[16], dec[16];
    double dra,ddec;
    double drarad,ddecrad;
    char *rahh,*ramm,*rass,*decdeg,*decmm,*decss;
    char coords[80];
    int startIndex;
    double rarad;
    double decrad;
    int err;
    char sign;
    int ihmsf[4],idmsf[4];

    /* Read command-line arguments */
    if (argc != 5) {
        for (int i = 0; help[i] != 0; i++)
            fprintf (stdout, "%s\n", help[i]);
        exit (1);
    }
    sscanf(argv[1],"%s",ra);
    sscanf(argv[2],"%s",dec);
    sscanf(argv[3],"%lf",&dra);
    sscanf(argv[4],"%lf",&ddec);

    /* Tokenize the RA and Dec strings so we can re-format them 
     * into a single coordinate string in the format that SLALIB likes */
    rahh = strtok(ra,delims);
    ramm = strtok(NULL,delims);
    rass = strtok(NULL,delims);
    decdeg = strtok(dec,delims);
    decmm = strtok(NULL,delims);
    decss = strtok(NULL,delims);
    sprintf(coords,"%s %s %s %s %s %s", rahh,ramm,rass,decdeg,decmm,decss);

    /* Use SLALIB to convert this coordinate string into a pair of
     * coordinates in radians. */
    startIndex = 1; 
    slaDafin(coords, &startIndex, &rarad, &err);
    if (!err) {
        rarad *= 15.0;
    }
    else {
        fprintf(stderr,"Error parsing RA.\n");
        exit(1);
    }
    slaDafin(coords, &startIndex, &decrad, &err);
    if (err) {
        fprintf(stderr,"Error parsing Dec.\n");
        exit(1);
    }

    /* Add the offsets */
    rarad += dra/R2A;
    decrad += ddec/R2A;

    /* Pathological cases we must deal with by hand */
    if (rarad < 0.0)
        rarad += 2.0*PI;
    if (rarad > 2.0*PI)
        rarad -= 2.0*PI;
    if (decrad > PI/2.0)
        decrad = PI - decrad;
    if (decrad < -PI/2.0)
        decrad = -PI - decrad;

    /* Convert RA in radians to hour, min, sec, fraction */
    slaDr2tf(2,rarad,&sign,ihmsf);

    /* Convert Dec in radians to deg, min, sec, fraction */
    slaDr2af(2,decrad,&sign,idmsf);

    /* Store the position we want to go to in a string */
    sprintf(coords,"%2.2d:%2.2d:%2.2d.%2.2d %c%2.2d*%2.2d:%2.2d.%2.2d",
            ihmsf[0],ihmsf[1],ihmsf[2],ihmsf[3],
            sign,idmsf[0],idmsf[1],idmsf[2],idmsf[3]); 


    printf("%s\n",coords);

    exit(0);
}
