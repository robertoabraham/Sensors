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
"    calcseparation - calculate angular separation between coordinates",
"",
"SYNOPSIS",
"    % calcoffset ra1 dec1 ra2 dec2",
"",
"PARAMETERS",
"    ra1  - Right ascension in sexagesimal (HH:MM:SS.S) notation of first position",
"    dec1 - Declination in sexgesimal (sDD*MM:SS.S) notation of first position",
"    ra2  - Right ascension in sexagesimal (HH:MM:SS.S) notation of second position",
"    dec2 - Declination in sexgesimal (sDD*MM:SS.S) notation of second position",
"",
"EXAMPLES",
"",
"    % calcseparation 12:33:58.2 -00*15:15.2 12:03:13.3 -00*17:25.9", 
"",
"DESCRIPTION",
"",
"    This program computes the angular separation (in arcseconds) between two sets",
"    of celestial coordinate specified as HH:MM:SS.S sDD*MM:SS.S.",
"",
"    While this sounds trivial there are a sufficient number of subtleties that the",
"    the SLALIB library is used to do the coordinate conversion.  The code is designed",
"    handle pathological cases e.g. offsetting over the pole and across the 24h/0h line.",
"",
"AUTHOR",
"    Roberto Abraham (abraham@astro.utoronto.ca)",
"",
"LAST UPDATE",
"    August 2012",
0};


int main (int argc, char *argv[] ) {

    const char delims[]=":*d";
    char ra1[16], dec1[16];
    char ra2[16], dec2[16];
    char *rahh1,*ramm1,*rass1,*decdeg1,*decmm1,*decss1;
    char *rahh2,*ramm2,*rass2,*decdeg2,*decmm2,*decss2;
    char coords1[80];
    char coords2[80];
    int startIndex;
    double rarad1,decrad1;
    double rarad2,decrad2;
    double separation;
    int err;
    char sign;
    int ihmsf[4],idmsf[4];

    /* Read command-line arguments */
    if (argc != 5) {
        for (int i = 0; help[i] != 0; i++)
            fprintf (stdout, "%s\n", help[i]);
        exit (1);
    }
    sscanf(argv[1],"%s",ra1);
    sscanf(argv[2],"%s",dec1);
    sscanf(argv[3],"%s",ra2);
    sscanf(argv[4],"%s",dec2);

    /* Tokenize the RA and Dec strings so we can re-format them 
     * into a single coordinate string in the format that SLALIB likes */
    rahh1 = strtok(ra1,delims);
    ramm1 = strtok(NULL,delims);
    rass1 = strtok(NULL,delims);
    decdeg1 = strtok(dec1,delims);
    decmm1 = strtok(NULL,delims);
    decss1 = strtok(NULL,delims);
    sprintf(coords1,"%s %s %s %s %s %s", rahh1,ramm1,rass1,decdeg1,decmm1,decss1);

    rahh2 = strtok(ra2,delims);
    ramm2 = strtok(NULL,delims);
    rass2 = strtok(NULL,delims);
    decdeg2 = strtok(dec2,delims);
    decmm2 = strtok(NULL,delims);
    decss2 = strtok(NULL,delims);
    sprintf(coords2,"%s %s %s %s %s %s", rahh2,ramm2,rass2,decdeg2,decmm2,decss2);

    /* Use SLALIB to convert this coordinate string into a pair of
     * coordinates in radians. */
    startIndex = 1; 
    slaDafin(coords1, &startIndex, &rarad1, &err);
    if (!err) {
        rarad1 *= 15.0;
    }
    else {
        fprintf(stderr,"Error parsing RA position 1.\n");
        exit(1);
    }
    slaDafin(coords1, &startIndex, &decrad1, &err);
    if (err) {
        fprintf(stderr,"Error parsing Dec position 1.\n");
        exit(1);
    }

    startIndex = 1; 
    slaDafin(coords2, &startIndex, &rarad2, &err);
    if (!err) {
        rarad2 *= 15.0;
    }
    else {
        fprintf(stderr,"Error parsing RA position 2.\n");
        exit(1);
    }
    slaDafin(coords2, &startIndex, &decrad2, &err);
    if (err) {
        fprintf(stderr,"Error parsing Dec position 2.\n");
        exit(1);
    }

    /* Compute the separation in arcsec */
    separation = slaDsep(rarad1,decrad1,rarad2,decrad2)*R2A;

    printf("%lg\n",separation);

    exit(0);
}
