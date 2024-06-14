#include <stdio.h> 
#include <ctype.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <termios.h>

#define MAX_ATTEMPTS 3

char   *help[] = {
"",
"NAME",
"    position - slew telescope and/or report mount position",
"",
"SYNOPSIS",
"    % position [OPTIONS] ra dec  - slews telescope to (RA, Dec)",
"    % position [OPTIONS]         - reports telescope position",
"",
"OPTIONS",
"    -s        Report simulated position of 12:33:58.2 -00*15:15.2 44.23 183.3 West (used for testing scripts)",
"",
"PARAMETERS",
"    ra  - Right ascension in sexagesimal (HH:MM:SS.S) notation",
"    dec - Declination in sexgesimal (sDD*MM:SS.S) notation",
"",
"EXAMPLES",
"",
"    % position 12:33:58.2 -00*15:15.2 ",
"    % position",
"",
"DESCRIPTION",
"",
"    This program slews an Astro-Physics telescope mount to a celestial coordinates",
"    specified as HH:MM:SS.S sDD*MM:SS.S. If no arguments are supplied the program",
"    simply reports the current mount position.",
"",
"    The program assumes the serial port used to communicate with the mount is",
"    defined in the DRAGONFLY_MOUNT_SERIAL_PORT environment variable. If that",
"    variable isn't defined, it attempts to communicate on /dev/ttyUSB1.",
"",
"AUTHOR",
"    Roberto Abraham (abraham@astro.utoronto.ca)",
"",
"LAST UPDATE",
"    May 2012",
0};


int open_port(void)
{
    int fd; 
    struct termios options;
    char *portname;
    int max_portname_length=128;

    portname = getenv("DRAGONFLY_MOUNT_SERIAL_PORT");
    if (portname == NULL)
    {  
        portname = malloc(max_portname_length);
        strcpy(portname,"/dev/ttyUSB1");
    }

    fd = open(portname, O_RDWR | O_NOCTTY | O_NDELAY);
    if (fd == -1)
    {
        perror("Error - unable to open serial port.");
    }
    else {
        /* Set the port to use normal (blocking) mode */
        fcntl(fd, F_SETFL, 0);
        /* get the current options */
        tcgetattr(fd, &options);
        /* Control options: set to 9600 baud, no parity, 8 data bits, no flow control, 
         * 1 start bit, 1 stop bit. */
        cfsetispeed(&options, B9600);
        options.c_cflag &= ~PARENB;
        options.c_cflag &= ~CSTOPB;
        options.c_cflag &= ~CSIZE;
        options.c_cflag |= CS8;
        options.c_cflag |= (CLOCAL | CREAD); // Enable receive
        /* Local options: set raw input = disable ICANON, ECHO, ECHOE, and ISIG) */
        options.c_lflag     &= ~(ICANON | ECHO | ECHOE | ISIG);
        /* Output options: set raw output = disable post-processing */
        options.c_oflag     &= ~OPOST;
        /* Set read timeout */ 
        options.c_cc[VMIN]  = 0;
        options.c_cc[VTIME] = 10; // In 10ths of a second... so 10 = 1s timeout.
        /* set the options */
        tcsetattr(fd, TCSANOW, &options);
    }

    return (fd);
}


void print_help()
{
    for (int i = 0; help[i] != 0; i++)
        fprintf(stdout,"%s\n",help[i]);
}


int main(int argc, char *argv[])
{
    char buffer[255];  /* Input buffer */
    char *bufptr;      /* Current char in buffer */
    int  nbytes;       /* Number of bytes read */
    int  tries;        /* Number of tries so far */
    int  fd;           /* File descriptor for the port */
    char ra[16];
    char dec[16];
    char alt[16];
    char az[16];
    char ota[16];
    char version[16];
    char command[64];
    int check;
    int buffer_cleared = 0;
    int long_format_selected = 0;
    int ra_requested = 0;
    int dec_requested = 0;
    int alt_requested = 0;
    int az_requested = 0;
    int ota_requested = 0;
    int arg=1;
    int slew = 0;
    int c;
    char *cvalue = NULL;
    int sflag = 0;
    int narg;
    char portname[128];

    /* Parse command line options */ 
    opterr = 0;
    while ((c = getopt (argc, argv, "sh")) != -1)
        switch (c)
        {
            case 's':
                fprintf(stdout,"12:33:58.2 -00*15:15.2 44.23 183.3 West \n"); 
                return(0);
                break;
            case 'h':
                print_help();
                return(0);
                break;
            case '?':
                if (optopt == 'c')
                    fprintf (stderr, "Option -%c requires an argument.\n", optopt);
                else if (isprint (optopt))
                    fprintf (stderr, "Unknown option `-%c'.\n", optopt);
                else
                    fprintf (stderr,
                            "Unknown option character `\\x%x'.\n",
                            optopt);
                print_help();
                return 1;
            default:
                abort();
        }
     
    /* Handle non-option arguments */
    narg = argc - optind;
    if (narg != 0 && narg != 2)
    {
        print_help();
        return(1);
    }
    if (narg == 2) 
    { 
        char *d;
        sscanf(argv[optind++],"%s",ra);
        sscanf(argv[optind++],"%s",dec);
        /* Fix the common error of specifying degrees with 'd' instead of '*' */
        d = strstr(dec,"d");
        if (d != NULL)
            *d='*';
        slew = 1;
    }


    fd = open_port();
    if (fd<0) 
        return(-1);


    /* Initiate communication. The idea is that we can try to talk to the
     * mount up to MAX_ATTEMPTS times. Each successful activity in this loop
     * is flagged so if multiple attempts are made we can skip over the stuff
     * that has already been done and start at the last thing that failed. */

    for (tries = 0; tries < MAX_ATTEMPTS; tries ++)
    {
        /* Clear the input buffer */
        if (!buffer_cleared){
            check = write(fd, "#", 1); 
            if (check != 1)
                continue;
            else
                buffer_cleared = 1;
        }

        /* Select long format */
        if (!long_format_selected){
            check = write(fd, ":U#", 3); 
            if (check != 3)
                continue;
            else
                long_format_selected = 1;
        }


        if (slew)
        {
            /* USER WANTS TO SEND THE MOUNT SOMEWHERE */

            /* Store commanded RA */
            if (!ra_requested)
            {
                sprintf(command,":Sr %s#\r",ra);
                check = write(fd, command, strlen(command)-1);
                /* Check command was written properly */
                if (check != (strlen(command)-1))
                    continue;
                /* Check command was accepted by the mount */
                bufptr = buffer;
                read(fd,bufptr,1);
                if (*bufptr != '1')
                    continue;
                ra_requested = 1;
            }

            /* Store commanded Dec */
            if (!dec_requested)
            {
                sprintf(command,":Sd %s#\r",dec);
                check = write(fd, command, strlen(command)-1);
                /* Check command was written properly */
                if (check != (strlen(command)-1))
                    continue;
                /* Check command was accepted by the mount */
                bufptr = buffer;
                read(fd,bufptr,1);
                if (*bufptr != '1')
                    continue;
                dec_requested = 1;
            }

            /* Move telescope */
            check = write(fd, ":MS#\r", 5);
            /* Check command was written properly */
            if (check != 5)
                continue;
            /* Check command was accepted by the mount */
            bufptr = buffer;
            read(fd,bufptr,1);
            if (*bufptr != '0') 
                continue; 

            /* If we made it here the slew was succesfully initiated so our job is done */
            close(fd);
            return(0);
        }
        else 
        {

            /* USER WANTS A STATUS REPORT */

            /* Request right ascension from mount */ 
            if (!ra_requested) { 
                check = write(fd, ":GR#\r", 5); 
                if (check != 5)
                    continue;
                else {
                    ra_requested = 1;
                    /* read characters into our string buffer until we get a hash mark */
                    bufptr = buffer;
                    while ((nbytes = read(fd, bufptr, buffer + sizeof(buffer) - bufptr - 1)) > 0)
                    {
                        bufptr += nbytes;
                        if (bufptr[-1] == '#')
                            break;
                    }
                    /* null terminate the string and store it. Since the string ends
                     * on a hash mark though we null-terminate it one byte before the 
                     * end so we don't have to deal with the hash later when printing
                     * the result out. */
                    *(bufptr -1) = '\0';
                    strcpy(ra,buffer);
                }
            }

            /* Request declination from mount */ 
            if (!dec_requested) { 
                check = write(fd, "#:GD#\r", 6); 
                if (check != 6)
                    continue;
                else {
                    dec_requested = 1;
                    /* read characters into our string buffer until we get a hash mark */
                    bufptr = buffer;
                    while ((nbytes = read(fd, bufptr, buffer + sizeof(buffer) - bufptr - 1)) > 0)
                    {
                        bufptr += nbytes;
                        if (bufptr[-1] == '#')
                            break;
                    }
                    /* null terminate the string and store it. Since the string ends
                     * on a hash mark though we null-terminate it one byte before the 
                     * end so we don't have to deal with the hash later when printing
                     * the result out. */
                    *(bufptr -1) = '\0';
                    strcpy(dec,buffer);
                }
            }

            /* Request altitude from mount */ 
            if (!alt_requested) { 
                check = write(fd, "#:GA#\r", 6); 
                if (check != 6)
                    continue;
                else {
                    alt_requested = 1;
                    /* read characters into our string buffer until we get a hash mark */
                    bufptr = buffer;
                    while ((nbytes = read(fd, bufptr, buffer + sizeof(buffer) - bufptr - 1)) > 0)
                    {
                        bufptr += nbytes;
                        if (bufptr[-1] == '#')
                            break;
                    }
                    /* null terminate the string and store it. Since the string ends
                     * on a hash mark though we null-terminate it one byte before the 
                     * end so we don't have to deal with the hash later when printing
                     * the result out. */
                    *(bufptr -1) = '\0';
                    strcpy(alt,buffer);
                }
            }

            /* Request azimuth from mount */ 
            if (!az_requested) { 
                check = write(fd, "#:GZ#\r", 6); 
                if (check != 6)
                    continue;
                else {
                    az_requested = 1;
                    /* read characters into our string buffer until we get a hash mark */
                    bufptr = buffer;
                    while ((nbytes = read(fd, bufptr, buffer + sizeof(buffer) - bufptr - 1)) > 0)
                    {
                        bufptr += nbytes;
                        if (bufptr[-1] == '#')
                            break;
                    }
                    /* null terminate the string and store it. Since the string ends
                     * on a hash mark though we null-terminate it one byte before the 
                     * end so we don't have to deal with the hash later when printing
                     * the result out. */
                    *(bufptr -1) = '\0';
                    strcpy(az,buffer);
                }
            } 
            
            /* Request ota side from mount */ 
            if (!ota_requested) { 
                check = write(fd, "#:pS#\r", 6); 

                if (check != 6)
                    continue;
                else {
                    ota_requested = 1;
                    /* read characters into our string buffer until we get a hash mark */
                    bufptr = buffer;
                    while ((nbytes = read(fd, bufptr, buffer + sizeof(buffer) - bufptr - 1)) > 0)
                    {
                        bufptr += nbytes;
                        if (bufptr[-1] == '#')
                            break;
                    }
                    /* null terminate the string and store it. Since the string ends
                     * on a hash mark though we null-terminate it one byte before the 
                     * end so we don't have to deal with the hash later when printing
                     * the result out. */
                    *(bufptr -1) = '\0';
                    strcpy(ota,buffer);
                }
            } 

        } /* Closing bracket for the if statement selecting between goto and position requests */

        /* If we made it here the communication with the mount was successful */
        if (!slew) 
        {
            fprintf(stdout,"%s ",ra);
            fprintf(stdout,"%s ",dec);
            fprintf(stdout,"%s ",alt);
            fprintf(stdout,"%s ",az);
            fprintf(stdout,"%s\n",ota);
        }

        close (fd);
        return (0);

    } /* Closing bracket for the main for loop */

    /* Failed to communicate with the mount... close up as neatly as possible. */
    fprintf(stderr,"Error. Position unavailable and/or goto failed.\n");
    close(fd);
    return (1);

}



