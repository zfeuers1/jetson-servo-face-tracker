#!/usr/bin/env python3
"""
Yahboom Servo Controller V2 - Optimized for high-performance tracking
Protocol: $<letter>0-180# at 9600 baud
S1 = A (pan/horizontal)
S2 = B (tilt/vertical)
"""

import serial
import time

class ServoController:
    def __init__(self, port="/dev/ttyTHS1", pan_center=90, tilt_center=95):
        """
        Initialize servo controller
        
        Args:
            port: Serial port (default: /dev/ttyTHS1)
            pan_center: Center angle for pan servo (default: 90)
            tilt_center: Center angle for tilt servo (default: 95, calibrated)
        """
        self.pan_center = pan_center
        self.tilt_center = tilt_center
        
        # Connect at 9600 baud as per docs
        # exclusive=True prevents other processes from opening the port
        self.ser = serial.Serial(port, 9600, timeout=0.1, exclusive=True)
        time.sleep(2)
        
        # Initialize servos to center
        self._send('A', self.pan_center)
        self._send('B', self.tilt_center)
        print(f"✓ Servo controller ready (center: pan={self.pan_center}° tilt={self.tilt_center}°)")
    
    def _send(self, letter, angle):
        """Send command: $<letter><angle>#"""
        angle = int(max(0, min(180, angle)))
        # Format angle as 3 digits with zero padding (e.g., 010, 090, 180)
        cmd = f"${letter}{angle:03d}#"
        self.ser.write(cmd.encode('ascii'))
        self.ser.flush()
        # No delay - servos handle timing internally, let them work at their own speed
    
    def set_servo(self, servo_letter, angle):
        """
        Set servo angle
        servo_letter: 'A' (S1), 'B' (S2), etc.
        angle: 0-180 degrees
        """
        self._send(servo_letter, angle)
    
    def pan(self, angle):
        """Set pan (horizontal) - Servo A"""
        self._send('A', angle)
    
    def tilt(self, angle):
        """Set tilt (vertical) - Servo B"""
        self._send('B', angle)
    
    def move(self, pan_angle, tilt_angle):
        """Set both pan and tilt"""
        self.pan(pan_angle)
        self.tilt(tilt_angle)
    
    def close(self):
        """Close connection"""
        self.move(self.pan_center, self.tilt_center)
        time.sleep(1)
        self.ser.close()


# Example usage
if __name__ == "__main__":
    print("Example: Control servos")
    
    controller = ServoController()
    
    try:
        # Example 1: Set individual servos
        print("\nSetting pan to 45°...")
        controller.pan(45)
        
        print("Setting tilt to 120°...")
        controller.tilt(120)
        
        # Example 2: Move both at once
        print("\nMoving to (90, 90)...")
        controller.move(90, 90)
        
        # Example 3: Sweep pan
        print("\nSweeping pan...")
        for angle in range(0, 181, 30):
            controller.pan(angle)
        
        controller.move(90, 90)
        
    finally:
        controller.close()

