* Arduino lens control.

** Installation

Download the latest Arduino IDE from here:

https://www.arduino.cc/en/Main/Software

Don't use apt-get as this installs an ancient version without full SPI support.

** Contents

*** Sketches

This directory contains the following Arduino sketches:

  - CanonLensControl - Arduino firmware sketch defining serial commands for 
    controlling a Canon 400mm f/2.8 IS II lens. Commands control the focus, diaphragm, 
    and image stabilization.

  - Remember when setting up the Arduino that the clock pin needs to pulled up. 
    Use a 10K resistor going from the clock pin (pin 13 on an Uno) to the 5V 
    VDD power.

*** Scripts - 

This directory contains the following scripts:

  - lens - script to send serial commands to the arduino.

