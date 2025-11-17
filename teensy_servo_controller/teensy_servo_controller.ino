/*
 * Teensy 4.1 Servo Controller for Face Tracker
 * 
 * Binary Protocol (115200 baud):
 * - 'P' + angle byte (0-180) = Pan servo
 * - 'T' + angle byte (0-180) = Tilt servo
 * 
 * Wiring:
 * - Pin 0 → Pan servo signal
 * - Pin 1 → Tilt servo signal
 * - GND → Servo GND + Power supply GND
 * - Servos powered from external 5-6V supply (NOT Teensy!)
 */

#include <Servo.h>

// Servo objects
Servo panServo;
Servo tiltServo;

// Pin definitions
const int PAN_PIN = 0;   // PWM pin for pan servo
const int TILT_PIN = 1;  // PWM pin for tilt servo

// Command protocol
// Format: 'P' angle(0-180) or 'T' angle(0-180)
// Example: P90 = Pan to 90 degrees
//          T45 = Tilt to 45 degrees

void setup() {
  // Initialize USB Serial
  Serial.begin(115200);
  
  // Attach servos to PWM pins
  panServo.attach(PAN_PIN);
  tiltServo.attach(TILT_PIN);
  
  // Center servos on startup
  panServo.write(90);
  tiltServo.write(95);
  
  // Wait for USB connection (Teensy will wait here until Jetson connects)
  while (!Serial) {
    delay(10);
  }
  
  // Send ready signal
  Serial.println("READY");
  
  // Built-in LED indicates ready
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);
}

void loop() {
  // Check for incoming commands
  if (Serial.available() >= 2) {
    char cmd = Serial.read();
    int angle = Serial.read();
    
    // Clamp angle to valid range
    angle = constrain(angle, 0, 180);
    
    // Execute command
    if (cmd == 'P') {
      panServo.write(angle);
    } 
    else if (cmd == 'T') {
      tiltServo.write(angle);
    }
    else {
      // Invalid command, flush buffer
      while (Serial.available()) {
        Serial.read();
      }
    }
  }
  
  // Blink LED to show we're running
  static unsigned long lastBlink = 0;
  if (millis() - lastBlink > 1000) {
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
    lastBlink = millis();
  }
}


