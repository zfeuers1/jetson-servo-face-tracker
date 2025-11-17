# Face Tracker

Real-time face tracking system using IMX477 camera and pan-tilt servos on Jetson Orin with Teensy 4.1 servo controller.

## Features

- **60fps camera** - Smooth 1080p video capture
- **Adaptive tracking** - Gentle approach, fast fine-tuning
- **30Hz servo updates** - Ultra-responsive tracking via Teensy 4.1
- **Intelligent dead zone** - Locks on when centered
- **Auto-search mode** - Scans room if you leave the frame
- **High-speed USB serial** - 115200 baud for minimal latency

## Hardware

### Required Components

- **Jetson Orin Nano Super Dev Kit**
- **Arducam IMX477** (12MP CSI camera)
- **Teensy 4.1** microcontroller
- **2x Hobby Servos** (pan and tilt)
  - Recommend: YB-P25M or similar 180° servos
- **Servo power supply** (5-6V, 2-3A capable)

## Wiring

### Camera Connection

- **IMX477** → Jetson **CAM0** or **CAM1**
- **Important**: Blue side of ribbon cable facing **UP** on both ends

### Teensy → Jetson

- **USB**: Teensy USB port → Jetson USB port
  - Appears as `/dev/ttyACM0`
  - No additional wiring needed!

### Teensy → Servos

- **Pan Servo** (horizontal):
  - Signal → Teensy Pin 0
  - Power → 5-6V supply (+)
  - Ground → Teensy GND + supply (-)

- **Tilt Servo** (vertical):
  - Signal → Teensy Pin 1
  - Power → 5-6V supply (+)
  - Ground → Teensy GND + supply (-)

**Important**: 
- Common ground between Teensy and servo power supply
- Do NOT power servos from Teensy 5V pin!
- Use separate regulated supply for servos

## Software Setup

### 1. Install Arduino CLI (for Teensy programming)

```bash
cd ~/Documents/face-tracker
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
sudo mv bin/arduino-cli /usr/local/bin/
```

### 2. Install Teensyduino

```bash
# Add Teensy board support
arduino-cli config init
arduino-cli config add board_manager.additional_urls https://www.pjrc.com/teensy/package_teensy_index.json
arduino-cli core update-index
arduino-cli core install teensy:avr

# Install Teensy loader
wget https://www.pjrc.com/teensy/teensy_loader_cli_2.2.tar.gz
tar -xzf teensy_loader_cli_2.2.tar.gz
cd teensy_loader_cli_2.2
make
sudo cp teensy_loader_cli /usr/local/bin/
cd ..
rm -rf teensy_loader_cli_2.2*
```

### 3. Install udev Rules (for Teensy permissions)

```bash
sudo wget https://www.pjrc.com/teensy/00-teensy.rules -O /etc/udev/rules.d/00-teensy.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### 4. Install Python Dependencies

```bash
# System packages
sudo apt-get update
sudo apt-get install python3-serial

# Python packages (user install)
pip3 install pyserial mediapipe
```

**Note:** Use system OpenCV (comes with Jetson) for GStreamer support. Don't install opencv-python via pip!

### 5. Program the Teensy

```bash
cd ~/Documents/face-tracker

# Create Arduino sketch folder
mkdir -p teensy_servo_controller
cp teensy_servo_controller.ino teensy_servo_controller/

# Compile
arduino-cli compile --fqbn teensy:avr:teensy41 teensy_servo_controller

# Upload (press white button on Teensy when prompted)
arduino-cli upload -p /dev/ttyACM0 --fqbn teensy:avr:teensy41 teensy_servo_controller
```

**Troubleshooting upload**: If upload fails, press the small **white button** on Teensy when you see "Waiting for device..."

## Usage

### Run Face Tracker

```bash
cd ~/Documents/face-tracker
python3 face_tracker.py
```

### Controls

- **ESC** - Exit the program
- Everything else is automatic!

### What You'll See

1. **Startup**: Servos move to starting position (pan=90°, tilt=45°)
2. **Tracking**: When it detects your face:
   - **"TRACKING (GENTLE)"** - Approaching from far away (smooth, no overshoot)
   - **"TRACKING (FAST)"** - Fine-tuning position (tight, responsive)
   - **"LOCKED ✓"** - Perfectly centered (stopped)
   - Green box around your face
   - Green dot = your face center
   - Blue crosshair = frame center
   - Red box = dead zone (lock zone)
3. **Search Mode**: If you leave the frame for 3 seconds, it scans the room

## How It Works

### Adaptive Tracking Algorithm

```
1. Detect face with MediaPipe (60fps)
2. Smooth face position (exponential filter)
3. Calculate error: face_center - frame_center
4. Calculate distance from center

5. SELECT GAIN:
   - If distance > 150px: Use GENTLE gain (0.008) → smooth approach
   - If distance < 150px: Use FAST gain (0.013) → tight tracking

6. Accumulate correction (handles servo dead band)
7. When accumulated > 1°: Send command to Teensy
8. If error < 40px: STOP (locked on)
```

### Key Parameters

```python
DEAD_ZONE = 40         # Pixels - lock zone
MIN_MOVE = 1           # Degrees - servo resolution
GAIN_FAR = 0.008       # Gentle gain when far
GAIN_NEAR = 0.013      # Fast gain when close
GAIN_THRESHOLD = 150   # Pixels - switch point
UPDATE_RATE = 30       # Hz - servo updates
SMOOTHING = 0.75       # Face position smoothing
```

## File Structure

```
face-tracker/
├── face_tracker.py              # Main tracking application
├── camera_utils.py              # GStreamer pipeline for IMX477
├── servo_controller.py          # USB serial control for Teensy
├── teensy_servo_controller.ino  # Arduino code for Teensy
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Calibration

### Center Position

If servos don't point straight ahead at startup, edit `face_tracker.py`:

```python
servos = ServoController(pan_center=90, tilt_center=95)
```

Adjust `pan_center` and `tilt_center` to your servo's actual center angles.

### Tracking Sensitivity

Edit parameters in `face_tracker.py`:

- **DEAD_ZONE**: Larger = stops further from center (more stable)
- **GAIN_FAR**: Larger = faster initial approach (may overshoot)
- **GAIN_NEAR**: Larger = more aggressive fine-tuning
- **GAIN_THRESHOLD**: Larger = uses gentle mode longer
- **UPDATE_RATE**: Higher = more responsive (may jitter)

## Troubleshooting

### Camera Issues

```bash
# Check if camera is detected
sudo i2cdetect -y -r 9

# Should show "UU" at address 0x1a (IMX477)
```

**Fix**: Power off, check ribbon cable orientation (blue UP on both ends), reconnect firmly.

**If GStreamer fails**: Try rebooting Jetson to reset Argus camera daemon.

### Teensy Issues

```bash
# Check if Teensy is connected
ls -la /dev/ttyACM0

# Check if Arduino CLI works
arduino-cli board list
```

**Fix - Upload fails**:
1. Press white button on Teensy
2. Run upload command within 15 seconds
3. LED should blink when programmed successfully

**Fix - Servo controller not responding**:
- Check USB cable (data capable, not charge-only)
- Verify servos connected to pins 0 and 1
- Check servo power supply is on
- Open Arduino Serial Monitor to see Teensy output

### Servo Issues

```bash
# Test Teensy is running
python3 -c "import serial; s = serial.Serial('/dev/ttyACM0', 115200, timeout=2); print(s.readline())"

# Should print: b'READY\r\n'
```

**Fix**:
- Make sure servos have separate power (not from Teensy!)
- Check common ground between Teensy and servo supply
- Verify signal wires on pins 0 (pan) and 1 (tilt)

### Performance Issues

```bash
# Check if using system OpenCV (has GStreamer)
python3 -c "import cv2; print(cv2.getBuildInformation())" | grep GStreamer

# Should show "YES"
```

**Fix**: Uninstall pip opencv: `pip3 uninstall opencv-python opencv-contrib-python`

## Technical Details

### Camera

- **Resolution**: 1920x1080 @ 60fps
- **Pipeline**: nvarguscamerasrc → nvvidconv → appsink
- **Processing**: MediaPipe BlazeFace (optimized for edge devices)
- **Latency**: ~16ms per frame

### Teensy Servo Controller

- **Protocol**: Binary (2 bytes per command)
  - Byte 1: Command ('P' = pan, 'T' = tilt)
  - Byte 2: Angle (0-180)
- **Baudrate**: 115200 (high-speed)
- **Response time**: <5ms per command
- **Pins**: 
  - Pin 0 = Pan servo (PWM)
  - Pin 1 = Tilt servo (PWM)
- **Library**: Teensy built-in Servo library

### Control System

- **Type**: Adaptive proportional control with error accumulation
- **Dead zone**: Prevents jitter when locked on target
- **Smoothing**: Exponential moving average reduces noise
- **Gain switching**: Prevents overshoot on initial approach

### Why Teensy?

The Teensy 4.1 upgrade provides:
- **3x faster updates** (30Hz vs 10Hz with Yahboom)
- **10x lower latency** (5ms vs 200ms response time)
- **Smoother motion** (hardware PWM, no jitter)
- **Simpler wiring** (USB, no UART/level shifters)
- **More reliable** (direct servo control)

## Performance

- **Latency**: ~20ms camera-to-servo (total system)
- **Accuracy**: ±20px (40px dead zone)
- **Frame rate**: 60fps video, 30Hz servo updates
- **CPU usage**: ~15-20% on Jetson Orin
- **Tracking speed**: Adaptive (gentle approach, fast lock)

## Future Improvements

- [ ] Support multiple face tracking
- [ ] Add face recognition
- [ ] Implement predictive tracking (Kalman filter)
- [ ] Add video recording capability
- [ ] Speed ramping (ease-in/ease-out curves)

## License

MIT License - Feel free to use and modify!

## Credits

- Built for Jetson Orin Nano Super Dev Kit
- Uses MediaPipe for face detection
- Teensy 4.1 by PJRC
- Arducam IMX477 12MP Camera

---

**Enjoy your ultra-smooth face tracker!** 📷🤖
