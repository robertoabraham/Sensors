#include "Canon.h"
#include <EEPROM.h>

int16_t near;
int16_t infinite;
int16_t is_x;
int16_t is_y;

// Arduino UNO
// Pin 13 = Clock
// Pin 12 = MISO (DLC)
// Pin 11 = MOSI (DCL)

/*  
 * Commands
 * 
 * lp:  Check lens presence
 * in:  Open aperture
 * st:  Stop driving focus and aperture                                 
 * is1: IS unlock
 * ix:  IS shift in x-direction (ex: ix 100)
 * iy:  IS shift in y-direction (ex: iy 100)
 * is0: IS lock
 * pi:  Print IS position
 * mf:  Move focus incremental (ex: mf 100)
 * fa:  Move focus to absolute setpoint (ex: fa 100)
 * mi:  Move focus to infinity
 * mz:  Move focus to near
 * la:  Update fmax (infinity) and fmin (near)
 * pf:  Print focus position information
 * sf0: Focus position information is reset to 0
 * dc:  Disable output circuit
 * ec:  Enable output circuit
*/

void setup() {
  Serial.begin(9600);
  SPI.begin();
  SPI.beginTransaction(SPISettings(SPI_CLOCK_DIV128, MSBFIRST, SPI_MODE3));

  // Unclear why this is needed... but I'll leave it.
  pinMode(10, OUTPUT);
  digitalWrite(10, LOW); // Set pin 10 to be pulled down.

  // Set the Arduino's internal pull-up resistor on the MISO pin.
  pinMode(12, INPUT_PULLUP);
//  pinMode(11, OUTPUT);

  // Set new VDD control pin to low
  pinMode(2, OUTPUT);
  digitalWrite(2, LOW); // Set pin 2 to be low
  

  // Set up the tri-state buffer. This is used to control whether we are using LCLK on the lens
  // to send data to, or get data from, the lens.
  pinMode(TSB_OUTPUT_ENABLE_PIN, OUTPUT);          // Pin we set to activate sending data on LCLK to lens
  pinMode(TSB_INPUT_ENABLE_PIN, OUTPUT);           // Pin we set to activate getting data from LCLK on lens
//  digitalWrite(TSB_OUTPUT_ENABLE_PIN, TSB_ENABLE); // Enables output to the lens on LCLK
//  digitalWrite(TSB_INPUT_ENABLE_PIN, TSB_DISABLE); // Disables input from the lens on LCLK

  ///////////// SC edit ////////////////////
  //Start with the clock off
  digitalWrite(TSB_OUTPUT_ENABLE_PIN, TSB_DISABLE); // Disables output to the lens on LCLK
  digitalWrite(TSB_INPUT_ENABLE_PIN, TSB_ENABLE); // Enables input from the lens on LCLK

  // Set up the input port of the second tristate buffer, pull it up
  pinMode(TSB_LCLK_INPUT_PIN, INPUT_PULLUP);
  //digitalWrite(13, HIGH);
  ////////////////////////////////////////////
  

  // Get fmin, fmax, is_x, is_y that was stored in eeprom
  uint8_t value1;
  uint8_t value2;
  // fmin
  value1 = EEPROM.read(0);
  value2 = EEPROM.read(1);
  near = (int16_t) ((uint16_t) (value2 << 8)) | ((uint16_t) value1);
  // fmax
  value1 = EEPROM.read(2);
  value2 = EEPROM.read(3);
  infinite = (int16_t) ((uint16_t) (value2 << 8)) | ((uint16_t) value1);
  // is_x
  value1 = EEPROM.read(4);
  value2 = EEPROM.read(5);
  is_x = (int16_t) ((uint16_t) (value2 << 8)) | ((uint16_t) value1);
  // is_y
  value1 = EEPROM.read(6);
  value2 = EEPROM.read(7);
  is_y = (int16_t) ((uint16_t) (value2 << 8)) | ((uint16_t) value1);
}

void disable_clk(void){
  digitalWrite(TSB_OUTPUT_ENABLE_PIN, TSB_DISABLE);   // Disables output to lens
  digitalWrite(TSB_INPUT_ENABLE_PIN, TSB_ENABLE);     // Enables input from lens
  Serial.println("Output circuit disabled.");
}

unsigned int spi_transfer(unsigned int outgoingByte) {
  bool debug = true;
  digitalWrite(TSB_INPUT_ENABLE_PIN, TSB_DISABLE); // Disables input from the lens on LCLK
  digitalWrite(TSB_OUTPUT_ENABLE_PIN, TSB_ENABLE); // Enables output to the lens on LCLK
  uint8_t incomingByte = SPI.transfer(outgoingByte);
  digitalWrite(TSB_OUTPUT_ENABLE_PIN, TSB_DISABLE); // Disables output to the lens on LCLK
  digitalWrite(TSB_INPUT_ENABLE_PIN, TSB_ENABLE); // Enables input from the lens on LCLK
//  //choice 1: always wait 30ms, always works
//  delay(30); 
//  //choice 2: wait the shortest amount of time, but risk getting stuck in while loop
//  while(digitalRead(TSB_LCLK_INPUT_PIN) == HIGH);
//  while(digitalRead(TSB_LCLK_INPUT_PIN) == LOW); 
//  //choice 3: have a timeout that will take you out of the while loop after 1ms
  unsigned long stop1 = millis();
  while(((millis()-stop1)<1) && (digitalRead(TSB_LCLK_INPUT_PIN) == HIGH));
  unsigned long stop2 = millis();
  while(((millis()-stop2)<1) && (digitalRead(TSB_LCLK_INPUT_PIN) == LOW));
  digitalWrite(TSB_INPUT_ENABLE_PIN, TSB_DISABLE); // Disables input from the lens on LCLK
  digitalWrite(TSB_OUTPUT_ENABLE_PIN, TSB_ENABLE); // Enables output to the lens on LCLK
  
  if (debug) {
    Serial.print("SPI sent: ");
    Serial.println(outgoingByte, HEX);
    Serial.print("SPI received: ");
    Serial.println(incomingByte, HEX);
  }
  //delay(30);
  delay(1); //only need to delay 100us, delay 1000us to be safe
  // for tranfers with a short 'busy' time, sometimes it isn't caught by the while loop, run this to be safe
//  digitalWrite(TSB_INPUT_ENABLE_PIN, TSB_DISABLE); // Disables input from the lens on LCLK
//  digitalWrite(TSB_OUTPUT_ENABLE_PIN, TSB_ENABLE); // Enables output to the lens on LCLK
  return incomingByte;
}

int16_t print_focus() {
  spi_transfer(0xC0);
  uint8_t fpc1 = spi_transfer(0x00);
  uint8_t fpc2 = spi_transfer(0x00);
  return ((uint16_t) (fpc1 << 8)) | ((uint16_t) fpc2);
}

void move_focus_incremental(int16_t focus) {
  if (focus == 0) {
    Serial.println("Cannot have quantity of 0");
  } 
  else {
    uint8_t fcsdt1 = (uint8_t) (((uint16_t) focus) >> 8);
    uint8_t fcsdt2 = (uint8_t) focus;
    spi_transfer(0x44);
    spi_transfer(fcsdt1);
    spi_transfer(fcsdt2);
  }
}

void loop() {
  String command;
  while(true) {
    if (Serial.available() > 0) {
      delay(10);
      char c = (char) Serial.read();
      // Command ends with newline.
      if (c == '\n') {
        break;
      }
      command = command + String(c);
    }
  }
  Serial.flush();
  Serial.print("Command received: ");
  Serial.println(command);

  // Lens presence
  if (command == "lp") {
    spi_transfer(0x0A);
    spi_transfer(0x0A);
    spi_transfer(0x0A);
    uint8_t incomingByte = spi_transfer(0x00);
    if (incomingByte != 0xAA) {
      Serial.println("Lens not found.");
    }
    else {
      Serial.println("Lens is connected!");
    }
  }

  // Disable circuit
  else if (command == "dc") {
    digitalWrite(TSB_OUTPUT_ENABLE_PIN, TSB_DISABLE);   // Disables output to lens
    digitalWrite(TSB_INPUT_ENABLE_PIN, TSB_ENABLE);     // Enables input from lens
    Serial.println("Output circuit disabled.");
  }


  // Enable circuit
  else if (command == "ec") {
    digitalWrite(TSB_OUTPUT_ENABLE_PIN, TSB_ENABLE);    // Enables output to lens
    digitalWrite(TSB_INPUT_ENABLE_PIN, TSB_DISABLE);    // Disables input from lens
    Serial.println("Output circuit enabled.");
  }

///////// SC edit , not yet implemented, using pin 2 to control VDD to lens with MOSFET//////////////
//  // Restart VDD
//  else if (command == "rs") {
//    digitalWrite(2, HIGH);    //turn VDD off by setting Vgs=0, 0.5s, see MOSFET p-channel high side switch
//    Serial.println("VDD disabled.");
//    delay(500);
//    digitalWrite(TSB_OUTPUT_ENABLE_PIN, TSB_DISABLE);   // Disables output to lens
//    digitalWrite(TSB_INPUT_ENABLE_PIN, TSB_ENABLE);     // Enables input from lens
//    digitalWrite(2, LOW);    // turn VDD on by setting vgs=-5
//    Serial.println("VDD enabled.");
//  }
//
//  else if (command == "lrs") {
//
//    digitalWrite(2, HIGH);    //turn VDD off by setting Vgs=0,10s, see MOSFET p-channel high side switch
//    Serial.println("VDD disabled.");
//    delay(10000);
//    digitalWrite(TSB_OUTPUT_ENABLE_PIN, TSB_DISABLE);   // Disables output to lens
//    digitalWrite(TSB_INPUT_ENABLE_PIN, TSB_ENABLE);     // Enables input from lens
//    digitalWrite(2, LOW);    // turn VDD on by setting vgs=-5
//    Serial.println("VDD enabled.");
//  }
//////////////////////////////////////////////////////////////////////////////////

  // Open aperture
  else if (command == "in") {
    spi_transfer(0x13);
    spi_transfer(0x80);
    //spi_transfer(0x00);
  }

  // Stop driving focus and aperture
  // Note: not a Birger command
  else if (command == "st") {
    spi_transfer(0x09);
  }

  // IS unlock
  else if (command == "is1") {
    // Unlock the IS
    spi_transfer(0x0F);
    spi_transfer(0x91);
    spi_transfer(0xA8);
    spi_transfer(0x00);
    spi_transfer(0x00);
    spi_transfer(0x0F);
    spi_transfer(0x91);
    spi_transfer(0xA8);
    spi_transfer(0x00);
    spi_transfer(0x00);
    delay(500);

    // Confirm IS is unlocked
    spi_transfer(0x7A);
    spi_transfer(0x70);
    spi_transfer(0xFF);
    spi_transfer(0xFF);
    spi_transfer(0x71);
    spi_transfer(0xFE);
    uint8_t output = spi_transfer(0x00);
    if ((output & 0x01) != 0x01) {
      Serial.println("IS did not unlock");
    }
  }

  // IS shift in x-direction
  // Note: not a Birger command
  else if (command.substring(0,2) == "ix") {
    int16_t x = (int16_t) command.substring(2).toInt();
    Serial.print("Target position entered: " );
    Serial.println(x);

    uint8_t xdata1 = (uint8_t) (((uint16_t) x) >> 8);
    uint8_t xdata2 = (uint8_t) x;

    spi_transfer(0x72);
    spi_transfer(0xFF);
    spi_transfer(0x74);
    spi_transfer(0x66);
    spi_transfer(xdata1);
    spi_transfer(xdata2);

    is_x = x;
    uint8_t value1 = (uint8_t) is_x;
    uint8_t value2 = (uint8_t) (((uint16_t) is_x) >> 8);
    EEPROM.write(4, value1);
    EEPROM.write(5, value2);
  }

  // IS shift in y-direction
  // Note: not a Birger command
  else if (command.substring(0,2) == "iy") {
    int16_t y = (int16_t) command.substring(2).toInt();
    Serial.print("Target position entered: " );
    Serial.println(y);

    uint8_t ydata1 = (uint8_t) (((uint16_t) y) >> 8);
    uint8_t ydata2 = (uint8_t) y;

    spi_transfer(0x72);
    spi_transfer(0xFF);
    spi_transfer(0x76);
    spi_transfer(0x66);
    spi_transfer(ydata1);
    spi_transfer(ydata2);

    is_y = y;
    uint8_t value1 = (uint8_t) is_y;
    uint8_t value2 = (uint8_t) (((uint16_t) is_y) >> 8);
    EEPROM.write(6, value1);
    EEPROM.write(7, value2);
  }

  // IS lock
  else if (command == "is0") {
    // Shift IS back to centre along X direction
    spi_transfer(0x72);
    spi_transfer(0xFF);
    spi_transfer(0x74);
    spi_transfer(0x66);
    spi_transfer(0x00);
    spi_transfer(0x00);

    // Shift IS back to centre along Y direction
    spi_transfer(0x72);
    spi_transfer(0xFF);
    spi_transfer(0x76);
    spi_transfer(0x66);
    spi_transfer(0x00);
    spi_transfer(0x00);

    // Lock IS
    spi_transfer(0x0F);
    spi_transfer(0x91);
    spi_transfer(0x28);
    spi_transfer(0x00);
    spi_transfer(0x00);
  }

  // Print IS position
  else if (command == "pi") {
    Serial.print("is x postion: ");
    Serial.print(is_x);
    Serial.print(" is y position: ");
    Serial.println(is_y);
  }

  // Move focus incremental
  else if (command.substring(0,2) == "mf") {
    int16_t focus = (int16_t) command.substring(2).toInt();
    Serial.print("Relative focus quantity entered: " );
    Serial.println(focus);
    move_focus_incremental(focus);
  }

  // Move focus to absolute setpoint
  else if (command.substring(0,2) == "fa") {
    int16_t focus = (int16_t) command.substring(2).toInt();
    Serial.print("Absolute focus quantity entered: " );
    Serial.println(focus);
    int16_t fpc = print_focus();
    move_focus_incremental((focus-fpc));
  }

  // Move focus to infinity
  else if (command == "mi") {
    spi_transfer(0x05);
    delay(3000);
    infinite = print_focus();
    uint8_t value1 = (uint8_t) infinite;
    uint8_t value2 = (uint8_t) (((uint16_t) infinite) >> 8);
    EEPROM.write(2, value1);
    EEPROM.write(3, value2);
  }

  // Move focus to near (zero position)
  else if (command == "mz") {
    spi_transfer(0x06);
    delay(3000);
    near = print_focus();
    uint8_t value1 = (uint8_t) near;
    uint8_t value2 = (uint8_t) (((uint16_t) near) >> 8);
    EEPROM.write(0, value1);
    EEPROM.write(1, value2);
  }

  // Get fmax and fmin
  else if (command == "la") {
    spi_transfer(0x05);
    delay(3000);
    infinite = print_focus();
    uint8_t value1 = (uint8_t) infinite;
    uint8_t value2 = (uint8_t) (((uint16_t) infinite) >> 8);
    EEPROM.write(2, value1);
    EEPROM.write(3, value2);

    spi_transfer(0x06);
    delay(3000);
    near = print_focus();
    value1 = (uint8_t) near;
    value2 = (uint8_t) (((uint16_t) near) >> 8);
    EEPROM.write(0, value1);
    EEPROM.write(1, value2);
  }

  // Print focus position information
  else if (command == "pf") {
    int16_t fpc = print_focus();
    Serial.print("Focus position: ");
    Serial.println(fpc);
  }

  // Lens status
  else if (command == "fp") {
    int16_t fpc = print_focus();
    Serial.print("fmin: ");
    Serial.print(near);
    Serial.print(" fmax: ");
    Serial.print(infinite);
    Serial.print(" current: ");
    Serial.println(fpc);
  }

  // Focus position information is reset to 0 (does not drive lens)
  else if (command == "sf0") {
    spi_transfer(0x0C);
  }

  else {
    Serial.println("Command entered is not valid");
  }

  Serial.println("Done.");
  
}
