#!/usr/bin/env python3
"""
Teensy 4.1 Servo Controller - High-speed servo control
Protocol: Binary commands over USB Serial at 115200 baud
Pan = P (servo on pin 0)
Tilt = T (servo on pin 1)
"""

import serial
import time

class ServoController:
    def __init__(self, port="/dev/ttyACM0", pan_center=90, tilt_center=95):
        """
        Initialize Teensy servo controller
        
        Args:
            port: USB serial port (default: /dev/ttyACM0)
            pan_center: Center angle for pan servo (default: 90)
            tilt_center: Center angle for tilt servo (default: 95)
        """
        self.pan_center = pan_center
        self.tilt_center = tilt_center
        
        # Connect at 115200 baud (much faster than Yahboom's 9600!)
        self.ser = serial.Serial(port, 115200, timeout=1)
        time.sleep(2)  # Wait for Teensy to initialize
        
        # Wait for READY signal from Teensy
        ready = False
        start_time = time.time()
        while not ready and (time.time() - start_time) < 5:
            if self.ser.in_waiting:
                line = self.ser.readline().decode('ascii').strip()
                if line == "READY":
                    ready = True
                    break
        
        if not ready:
            print("⚠ Warning: Teensy did not send READY signal")
        
        # Initialize servos to center
        self.pan(self.pan_center)
        self.tilt(self.tilt_center)
        print(f"✓ Teensy servo controller ready (center: pan={self.pan_center}° tilt={self.tilt_center}°)")
    
    def _send(self, cmd, angle):
        """
        Send binary command to Teensy
        Format: <cmd_byte><angle_byte>
        """
        angle = int(max(0, min(180, angle)))
        # Send as 2 bytes: command + angle
        self.ser.write(bytes([ord(cmd), angle]))
        self.ser.flush()
    
    def pan(self, angle):
        """Set pan (horizontal) - Pin 0"""
        self._send('P', angle)
    
    def tilt(self, angle):
        """Set tilt (vertical) - Pin 1"""
        self._send('T', angle)
    
    def move(self, pan_angle, tilt_angle):
        """Set both pan and tilt"""
        self.pan(pan_angle)
        self.tilt(tilt_angle)
    
    def close(self):
        """Close connection and center servos"""
        self.move(self.pan_center, self.tilt_center)
        time.sleep(0.5)
        self.ser.close()


# Example usage
if __name__ == "__main__":
    print("Teensy Servo Controller Test")
    print("=" * 50)
    
    try:
        controller = ServoController()
        
        print("\n1. Testing pan servo (pin 0)...")
        controller.pan(45)
        time.sleep(1)
        controller.pan(135)
        time.sleep(1)
        controller.pan(90)
        time.sleep(1)
        
        print("\n2. Testing tilt servo (pin 1)...")
        controller.tilt(45)
        time.sleep(1)
        controller.tilt(135)
        time.sleep(1)
        controller.tilt(95)
        time.sleep(1)
        
        print("\n3. Circular motion test...")
        positions = [
            (90, 45),   # center-down
            (135, 45),  # right-down
            (135, 95),  # right-center
            (135, 135), # right-up
            (90, 135),  # center-up
            (45, 135),  # left-up
            (45, 95),   # left-center
            (45, 45),   # left-down
            (90, 45),   # back to start
        ]
        
        for pan, tilt in positions:
            controller.move(pan, tilt)
            time.sleep(0.3)
        
        # Return to center
        controller.move(90, 95)
        print("\n✓ Test complete!")
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
    finally:
        controller.close()
        print("Servo controller closed")
