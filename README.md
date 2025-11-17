# Face Tracker

Real-time face tracking system using IMX477 camera and pan-tilt servos on Jetson Orin with Teensy 4.1.

## Hardware Required

- **Jetson Orin Nano Super Dev Kit**
- **Arducam IMX477** (12MP CSI camera)
- **Teensy 4.1** microcontroller
- **2x Hobby Servos** (pan and tilt, 180° range recommended)
- **5-6V Power Supply** for servos (2-3A capable)
- **USB cable** (Teensy to Jetson)
- **CSI ribbon cable** (included with camera)

## Wiring

### 1. Camera → Jetson

- Connect **IMX477** to Jetson **CAM0** or **CAM1** port
- **Blue side of ribbon UP** on both camera and Jetson

### 2. Teensy → Jetson

- Connect Teensy USB port to any Jetson USB port
- That's it! (appears as `/dev/ttyACM0`)

### 3. Servos → Teensy

**Pan Servo (horizontal rotation):**
- Signal wire → Teensy **Pin 0**
- Power (red) → 5-6V supply **+**
- Ground (black/brown) → Teensy **GND**

**Tilt Servo (vertical rotation):**
- Signal wire → Teensy **Pin 1**
- Power (red) → 5-6V supply **+**
- Ground (black/brown) → Teensy **GND**

**Important:**
- Connect Teensy GND to servo power supply GND (common ground)
- Do NOT power servos from Teensy - use external supply!

## Software Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/zfeuers1/jetson-servo-face-tracker.git
cd jetson-servo-face-tracker
```

### Step 2: Install Arduino CLI

```bash
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
sudo mv bin/arduino-cli /usr/local/bin/
```

### Step 3: Setup Teensy Support

**Option A - Automated (recommended):**
```bash
./setup_teensy.sh
```

**Option B - Manual:**
```bash
arduino-cli config init
arduino-cli config add board_manager.additional_urls https://www.pjrc.com/teensy/package_teensy_index.json
arduino-cli core update-index
arduino-cli core install teensy:avr

sudo wget https://www.pjrc.com/teensy/00-teensy.rules -O /etc/udev/rules.d/00-teensy.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Step 4: Install Python Dependencies

```bash
sudo apt-get update
sudo apt-get install python3-serial
pip3 install pyserial mediapipe
```

**Note:** Don't install `opencv-python` via pip - use Jetson's built-in OpenCV!

### Step 5: Program Teensy

**Option A - Automated (recommended):**
```bash
./program_teensy.sh
# Press the white button on Teensy when prompted
```

**Option B - Manual:**
```bash
arduino-cli compile --fqbn teensy:avr:teensy41 teensy_servo_controller
arduino-cli upload -p /dev/ttyACM0 --fqbn teensy:avr:teensy41 teensy_servo_controller
# Press the white button on Teensy when it says "Waiting for device"
```

## Running the Face Tracker

```bash
python3 face_tracker.py
```

**Controls:**
- **ESC** - Exit

**What you'll see:**
- Camera view with face detection box
- Green dot = your face center
- Blue crosshair = target center
- Red box = dead zone (stops when centered)
- Status: "TRACKING (GENTLE)" → "TRACKING (FAST)" → "LOCKED ✓"

## Calibration (Optional)

If servos don't center correctly, edit these values in `face_tracker.py`:

```python
servos = ServoController(pan_center=90, tilt_center=95)
```

Change `pan_center` and `tilt_center` to match your servo's center position.

## Troubleshooting

**Camera not found:**
```bash
sudo i2cdetect -y -r 9  # Should show "UU" at 0x1a
```
→ Check ribbon cable (blue side UP), power cycle Jetson

**Teensy not detected:**
```bash
ls /dev/ttyACM0  # Should exist
```
→ Check USB cable, try different port, run `./setup_teensy.sh` again

**Servos not moving:**
- Check servo power supply is ON
- Verify signal wires on pins 0 and 1
- Test Teensy: `python3 -c "import serial; s=serial.Serial('/dev/ttyACM0',115200,timeout=2); print(s.readline())"`
  - Should print `b'READY\r\n'`

**Import errors:**
- Don't use `sudo python3` - run as regular user
- Make sure `pip3 install` was done without sudo

## How It Works

The system uses adaptive gain control:
- **Far from center** (>150px): Gentle, smooth approach to prevent overshoot
- **Close to center** (<150px): Fast, tight tracking for precision
- **Centered** (<40px): Stops moving (locked on)

Face detection runs at 60fps, servos update at 30Hz via Teensy.

## License

MIT License

## Credits

- MediaPipe for face detection
- Teensy 4.1 by PJRC
- Arducam IMX477
