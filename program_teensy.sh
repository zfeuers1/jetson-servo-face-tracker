#!/bin/bash
# Program Teensy 4.1 with servo controller code

set -e  # Exit on error

echo "========================================"
echo "Programming Teensy 4.1"
echo "========================================"
echo ""

# Check if Teensy is connected
echo "1. Checking for Teensy..."
if lsusb | grep -i "teensy\|Van Ooijen" > /dev/null; then
    echo "   ✓ Teensy detected"
else
    echo "   ✗ Teensy not found!"
    echo "   Please connect Teensy to Jetson USB and try again."
    exit 1
fi

# Compile the code
echo ""
echo "2. Compiling code..."
arduino-cli compile --fqbn teensy:avr:teensy41 teensy_servo_controller

if [ $? -ne 0 ]; then
    echo "   ✗ Compilation failed!"
    exit 1
fi
echo "   ✓ Code compiled successfully"

# Upload to Teensy
echo ""
echo "3. Uploading to Teensy..."
echo ""
echo "   ⚠️  PRESS THE WHITE BUTTON ON TEENSY NOW!"
echo ""
echo "   The button is small and white, usually near the USB port."
echo "   Press it ONCE, then wait..."
echo ""

# Wait a moment for user to press button
sleep 2

arduino-cli upload -p /dev/ttyACM0 --fqbn teensy:avr:teensy41 teensy_servo_controller

if [ $? -ne 0 ]; then
    echo ""
    echo "   ✗ Upload failed!"
    echo ""
    echo "   Troubleshooting:"
    echo "   1. Did you press the white button on Teensy?"
    echo "   2. Try running this script again"
    echo "   3. Check USB connection"
    exit 1
fi

echo ""
echo "   ✓ Upload successful!"

# Verify it's running
echo ""
echo "4. Testing Teensy..."
sleep 2

if [ -e /dev/ttyACM0 ]; then
    echo "   ✓ Teensy is now running at /dev/ttyACM0"
    echo ""
    echo "   You can test it with:"
    echo "   python3 servo_controller.py"
else
    echo "   ⚠️  Waiting for Teensy to reboot..."
    sleep 2
    if [ -e /dev/ttyACM0 ]; then
        echo "   ✓ Teensy is ready at /dev/ttyACM0"
    fi
fi

echo ""
echo "========================================"
echo "✓ Programming complete!"
echo "========================================"
echo ""
echo "Next: Connect your servos and run:"
echo "  python3 servo_controller.py"

