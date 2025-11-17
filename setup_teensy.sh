#!/bin/bash
# Setup script to program Teensy 4.1 from Jetson Orin
# This installs Arduino CLI and programs the Teensy

set -e  # Exit on error

echo "========================================"
echo "Teensy 4.1 Setup for Jetson Orin"
echo "========================================"
echo ""

# Check if Teensy is connected
echo "1. Checking for Teensy connection..."
if lsusb | grep -i "teensy\|Van Ooijen" > /dev/null; then
    echo "   ✓ Teensy detected via USB"
else
    echo "   ✗ Teensy not detected!"
    echo ""
    echo "   Please connect Teensy to Jetson USB port now."
    echo "   Then press Enter to continue..."
    read
fi

# Install Arduino CLI
echo ""
echo "2. Installing Arduino CLI..."
if ! command -v arduino-cli &> /dev/null; then
    echo "   Downloading Arduino CLI..."
    cd /tmp
    curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
    sudo mv /tmp/bin/arduino-cli /usr/local/bin/
    echo "   ✓ Arduino CLI installed"
else
    echo "   ✓ Arduino CLI already installed"
fi

# Initialize Arduino CLI
echo ""
echo "3. Initializing Arduino CLI..."
arduino-cli config init --overwrite

# Add Teensy board manager URL
echo ""
echo "4. Adding Teensy board support..."
arduino-cli config add board_manager.additional_urls https://www.pjrc.com/teensy/package_teensy_index.json

# Update index
echo ""
echo "5. Updating board index..."
arduino-cli core update-index

# Install Teensy core
echo ""
echo "6. Installing Teensy core (this may take a few minutes)..."
arduino-cli core install teensy:avr

# Install Servo library
echo ""
echo "7. Installing Servo library..."
arduino-cli lib install Servo

echo ""
echo "========================================"
echo "✓ Setup complete!"
echo "========================================"
echo ""
echo "Next step: Run ./program_teensy.sh to upload code to Teensy"


