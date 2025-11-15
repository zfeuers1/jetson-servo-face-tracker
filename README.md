# Face Tracker

Real-time face tracking system using IMX477 camera and pan-tilt servos on Jetson Orin.

## Features

- **60fps camera** - Smooth 1080p video capture
- **Automatic face tracking** - Keeps you centered in frame
- **Simple proportional control** - Smooth servo movement
- **Adaptive dead zone** - Stops adjusting when "close enough"
- **Auto-search mode** - Scans room if you leave the frame

## Hardware

- **Jetson Orin Nano Super Dev Kit**
- **Arducam IMX477** (12MP CSI camera)
- **Yahboom 24-Servo Board** with 2x YB-P25M servos
  - S1 (A) = Pan (horizontal)
  - S2 (B) = Tilt (vertical)

## Wiring

### Camera
- IMX477 connected to **CAM0** or **CAM1**
- Blue side of ribbon cable facing **UP** on both ends

### Servos
- **Jetson UART** → **Yahboom Board**
  - Pin 8 (TX) → RX
  - Pin 10 (RX) → TX
  - GND → GND
- **Separate 7.4V power** to Yahboom board (2-3A capable)
- **No level shifter needed** (STM32 is 3.3V logic)

## Software Setup

### 1. Install Dependencies

```bash
# System packages
sudo apt-get update
sudo apt-get install python3-serial

# Python packages (user install)
pip3 install mediapipe
```

**Note:** Use system OpenCV (comes with Jetson) for GStreamer support. Don't install opencv-python via pip!

### 2. Add User to dialout Group

```bash
sudo usermod -a -G dialout $USER
# Then log out and back in
```

## Usage

### Run Face Tracker

```bash
cd ~/Documents/face-tracker
python3 face_tracker.py
```

### Controls

- **ESC** - Exit the program
- That's it! Everything else is automatic.

### What It Does

1. **Startup**: Servos move to starting position (pan=90°, tilt=45°)
2. **Tracking**: When it detects your face:
   - Green box around your face
   - Green dot = your face center
   - Blue crosshair = frame center
   - Yellow line = tracking error
   - "LOCKED ✓" when you're centered
3. **Search Mode**: If you leave the frame for 3 seconds, it scans the room

## How It Works

### Tracking Algorithm

```
1. Detect face with MediaPipe (60fps)
2. Smooth face position (exponential filter)
3. Calculate error: face_center - frame_center
4. If error > 150px: accumulate correction
5. When accumulated correction > 5°: move servo
6. If error < 150px: STOP (locked on)
```

### Key Parameters

```python
DEAD_ZONE = 150     # Pixels - "close enough" zone
MIN_MOVE = 5        # Degrees - servo dead band
GAIN = 0.02         # Degrees per pixel of error
UPDATE_RATE = 10    # Hz - servo update frequency
```

## File Structure

```
face-tracker/
├── face_tracker.py       # Main tracking application
├── camera_utils.py       # GStreamer pipeline for IMX477
├── servo_controller.py   # UART servo control
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Calibration

### Center Position

If your servos don't point straight ahead at startup, edit `face_tracker.py`:

```python
servos = ServoController(pan_center=90, tilt_center=95)
```

Adjust `pan_center` and `tilt_center` to your servo's actual center angles.

### Tracking Sensitivity

Edit parameters in `face_tracker.py`:

- **DEAD_ZONE**: Larger = stops further from center (more stable)
- **GAIN**: Larger = faster tracking (less stable)
- **UPDATE_RATE**: Higher = more responsive (may jitter)

## Troubleshooting

### Camera Issues

```bash
# Check if camera is detected
sudo i2cdetect -y -r 9

# Should show "UU" at address 0x1a
```

**Fix:** Power off, check ribbon cable orientation (blue UP on both ends), reconnect firmly.

### Servo Issues

```bash
# Check serial port
ls -la /dev/ttyTHS1

# Check group membership
groups
# Should include "dialout"
```

**Fix:** Make sure power switch on Yahboom board is ON!

### Performance Issues

```bash
# Check if using system OpenCV (has GStreamer)
python3 -c "import cv2; print(cv2.getBuildInformation())" | grep GStreamer

# Should show "YES"
```

**Fix:** Uninstall pip opencv: `pip3 uninstall opencv-python opencv-contrib-python`

## Technical Details

### Camera
- **Resolution**: 1920x1080 @ 60fps
- **Pipeline**: nvarguscamerasrc → nvvidconv → appsink
- **Processing**: MediaPipe face detection (optimized for edge devices)

### Servos
- **Protocol**: Text-based `$<letter><angle>#` at 9600 baud
- **Format**: `$A090#` = Set servo A to 90°
- **Range**: 0-180° (3-digit zero-padded)
- **Response time**: ~200ms per movement

### Control System
- **Type**: Simple proportional control with error accumulation
- **Dead zone**: Prevents micro-adjustments within servo precision limits
- **Smoothing**: Exponential moving average on face position

## Performance

- **Latency**: ~100ms camera-to-servo
- **Accuracy**: ±80px (servo precision limit)
- **Frame rate**: 60fps video, 10Hz servo updates
- **CPU usage**: ~15-20% on Jetson Orin

## Future Improvements

- [ ] Add manual control mode (WASD keys)
- [ ] Support multiple face tracking
- [ ] Add face recognition
- [ ] Implement predictive tracking (Kalman filter)
- [ ] Add video recording capability

## License

MIT License - Feel free to use and modify!

## Credits

- Built for Jetson Orin Nano Super Dev Kit
- Uses MediaPipe for face detection
- Yahboom 24-Servo Driver Board
- Arducam IMX477 12MP Camera

---

**Enjoy your working face tracker!** 📷🤖
