#!/usr/bin/env python3
"""
Face Tracker - Real-time face tracking with Teensy servo control
Uses proportional control with velocity limiting and search patterns
"""

import cv2
import mediapipe as mp
import time
from typing import Tuple
from camera_utils import gstreamer_pipeline
from servo_controller import ServoController

# MediaPipe face detection
mp_face_detection = mp.solutions.face_detection

# Tracking parameters - BALANCED
DEAD_ZONE = 40       # Pixels - tight but stable
MIN_MOVE = 1           # Degrees - fine adjustments
GAIN = 0.011           # Balanced gain
UPDATE_RATE = 30       # Hz - full speed
SMOOTHING = 0.4        # Some smoothing for stability
MAX_MOVE_PER_UPDATE = 18  # Cap big jumps

# Servo limits
PAN_MIN = 10
PAN_MAX = 170
TILT_MIN = 30
TILT_MAX = 120

# Search parameters
SEARCH_DELAY = 3.0
SEARCH_PAN_MIN = 40
SEARCH_PAN_MAX = 140
SEARCH_TILT_POSITIONS = [40, 50, 60]
SEARCH_STEP = 10
SEARCH_UPDATE_RATE = 5  # Hz - much slower than tracking (5 moves/sec)

# Display colors (BGR format)
COLOR_LOCKED = (0, 255, 0)      # Green
COLOR_TRACKING = (0, 200, 255)  # Yellow
COLOR_SEARCHING = (255, 165, 0) # Orange
COLOR_WAITING = (150, 150, 150) # Gray
COLOR_FACE_BOX = (0, 255, 0)    # Green
COLOR_FACE_CENTER = (0, 255, 0) # Green
COLOR_ERROR_LINE = (0, 255, 255) # Yellow
COLOR_DEADZONE = (100, 100, 255) # Purple
COLOR_CROSSHAIR = (255, 0, 0)   # Blue
COLOR_TEXT = (255, 255, 255)    # White
COLOR_INFO = (180, 180, 180)    # Light gray

# Display sizes
CROSSHAIR_SIZE = 30
FACE_BOX_THICKNESS = 3
FACE_CENTER_RADIUS = 10
DEADZONE_THICKNESS = 2
CROSSHAIR_THICKNESS = 3
STATUS_FONT_SCALE = 1.5
STATUS_THICKNESS = 3
SERVO_FONT_SCALE = 0.7
SERVO_THICKNESS = 2
INFO_FONT_SCALE = 0.6
INFO_THICKNESS = 1
TEXT_MARGIN = 10
SERVO_TEXT_OFFSET = 60
INFO_TEXT_OFFSET = 20

# Window settings
WINDOW_TITLE = "Face Tracker"

# Camera settings
CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080
CAMERA_FPS = 60

# Initial servo positions
SERVO_PAN_START = 90
SERVO_TILT_START = 45
SERVO_PAN_CENTER = 90
SERVO_TILT_CENTER = 95


def clamp(value, min_val, max_val):
    """Clamp value between min and max"""
    return max(min_val, min(max_val, value))


def get_face_center(detection, frame_width: int, frame_height: int) -> Tuple[int, int]:
    """Get the center point of a detected face"""
    bbox = detection.location_data.relative_bounding_box
    center_x = int((bbox.xmin + bbox.width / 2) * frame_width)
    center_y = int((bbox.ymin + bbox.height / 2) * frame_height)
    return center_x, center_y


def get_face_bbox(detection, frame_width: int, frame_height: int) -> Tuple[int, int, int, int]:
    """Get bounding box of detected face"""
    bbox = detection.location_data.relative_bounding_box
    x1 = int(bbox.xmin * frame_width)
    y1 = int(bbox.ymin * frame_height)
    w = int(bbox.width * frame_width)
    h = int(bbox.height * frame_height)
    return x1, y1, x1 + w, y1 + h


class ExponentialSmoother:
    """Exponential moving average for position smoothing"""
    
    def __init__(self, alpha: float):
        self.alpha = alpha
        self.value = None
    
    def update(self, new_value: float) -> float:
        """Update with new value, return smoothed value"""
        if self.value is None:
            self.value = new_value
        else:
            self.value = self.alpha * new_value + (1 - self.alpha) * self.value
        return self.value
    
    def reset(self):
        self.value = None


def update_servo_axis(error, accumulated, current_angle, min_angle, max_angle):
    """
    Update a single servo axis (pan or tilt) with proportional control
    Returns: (new_angle, new_accumulated, command_sent)
    """
    move = -error * GAIN
    move = clamp(move, -MAX_MOVE_PER_UPDATE, MAX_MOVE_PER_UPDATE)
    accumulated += move
    
    if abs(accumulated) >= MIN_MOVE:
        new_angle = clamp(current_angle + accumulated, min_angle, max_angle)
        return new_angle, 0.0, True
    
    return current_angle, accumulated, False


def draw_overlay(frame, pan_angle, tilt_angle, status, status_color):
    """Draw basic overlay (crosshair, status, servo info)"""
    height, width = frame.shape[:2]
    center_x, center_y = width // 2, height // 2
    
    # Center crosshair
    cv2.line(frame, (center_x - CROSSHAIR_SIZE, center_y), (center_x + CROSSHAIR_SIZE, center_y), 
             COLOR_CROSSHAIR, CROSSHAIR_THICKNESS)
    cv2.line(frame, (center_x, center_y - CROSSHAIR_SIZE), (center_x, center_y + CROSSHAIR_SIZE), 
             COLOR_CROSSHAIR, CROSSHAIR_THICKNESS)
    
    # Status text
    cv2.putText(frame, status, (TEXT_MARGIN, 50), cv2.FONT_HERSHEY_SIMPLEX, 
                STATUS_FONT_SCALE, status_color, STATUS_THICKNESS)
    
    # Servo angles
    servo_text = f"Pan:{pan_angle:.1f}deg  Tilt:{tilt_angle:.1f}deg"
    cv2.putText(frame, servo_text, (TEXT_MARGIN, height - SERVO_TEXT_OFFSET), 
                cv2.FONT_HERSHEY_SIMPLEX, SERVO_FONT_SCALE, COLOR_TEXT, SERVO_THICKNESS)
    
    # Info line
    info_text = f"Tracking | {UPDATE_RATE}Hz | Dead zone: {DEAD_ZONE}px | Max: {MAX_MOVE_PER_UPDATE}deg"
    cv2.putText(frame, info_text, (TEXT_MARGIN, height - INFO_TEXT_OFFSET), 
                cv2.FONT_HERSHEY_SIMPLEX, INFO_FONT_SCALE, COLOR_INFO, INFO_THICKNESS)


def draw_tracking_overlay(frame, face_x, face_y, x1, y1, x2, y2, error_x, error_y, 
                          pan_angle, tilt_angle, status, status_color):
    """Draw tracking visualization with face detection overlay"""
    height, width = frame.shape[:2]
    center_x, center_y = width // 2, height // 2
    
    # Face detection box and center
    cv2.rectangle(frame, (x1, y1), (x2, y2), COLOR_FACE_BOX, FACE_BOX_THICKNESS)
    cv2.circle(frame, (int(face_x), int(face_y)), FACE_CENTER_RADIUS, COLOR_FACE_CENTER, -1)
    cv2.line(frame, (center_x, center_y), (int(face_x), int(face_y)), COLOR_ERROR_LINE, DEADZONE_THICKNESS)
    
    # Dead zone box
    cv2.rectangle(frame,
                  (center_x - DEAD_ZONE, center_y - DEAD_ZONE),
                  (center_x + DEAD_ZONE, center_y + DEAD_ZONE),
                  COLOR_DEADZONE, DEADZONE_THICKNESS)
    
    # Draw base overlay
    draw_overlay(frame, pan_angle, tilt_angle, status, status_color)


def main():
    """Main face tracking loop"""
    
    print("=" * 60)
    print("Face Tracker - FAST MODE")
    print("=" * 60)
    print()
    print("Controls:")
    print("  ESC - Exit")
    print()
    print("Features:")
    print(f"  • {CAMERA_FPS}fps camera")
    print(f"  • {UPDATE_RATE}Hz servo updates")
    print(f"  • Max {MAX_MOVE_PER_UPDATE}deg per update")
    print(f"  • Dead zone: {DEAD_ZONE}px")
    print()
    
    # Initialize servos
    print("Initializing servos...")
    try:
        servos = ServoController(pan_center=SERVO_PAN_CENTER, tilt_center=SERVO_TILT_CENTER)
    except Exception as e:
        print(f"✗ Failed to initialize servos: {e}")
        return
    
    # Start position
    pan_angle = float(SERVO_PAN_START)
    tilt_angle = float(SERVO_TILT_START)
    servos.move(int(pan_angle), int(tilt_angle))
    print(f"✓ Starting position: Pan={pan_angle:.0f}deg Tilt={tilt_angle:.0f}deg")
    
    # Create GStreamer pipeline
    pipeline = gstreamer_pipeline(
        sensor_id=0,
        capture_width=CAMERA_WIDTH,
        capture_height=CAMERA_HEIGHT,
        display_width=CAMERA_WIDTH,
        display_height=CAMERA_HEIGHT,
        framerate=CAMERA_FPS,
        flip_method=0,
    )
    
    # Open camera
    print("Opening camera...")
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    
    if not cap.isOpened():
        print("✗ Failed to open camera")
        servos.close()
        return
    
    print(f"✓ Camera opened at {CAMERA_WIDTH}x{CAMERA_HEIGHT}@{CAMERA_FPS}fps")
    print()
    print("Starting high-performance tracking...")
    print()
    
    # Initialize face detection
    face_detection = mp_face_detection.FaceDetection(
        model_selection=0,
        min_detection_confidence=0.5
    )
    
    # Smoothing for face position
    face_x_smoother = ExponentialSmoother(SMOOTHING)
    face_y_smoother = ExponentialSmoother(SMOOTHING)
    
    # Timing
    servo_update_interval = 1.0 / UPDATE_RATE
    search_update_interval = 1.0 / SEARCH_UPDATE_RATE
    last_servo_update = time.time()
    last_search_update = time.time()
    last_face_time = time.time()
    
    # Error accumulation to handle sub-threshold corrections
    accumulated_pan = 0.0
    accumulated_tilt = 0.0
    
    # Search state
    searching = False
    search_direction = 1
    search_tilt_index = 0
    
    try:
        while True:
            loop_start = time.time()
            
            ret, frame = cap.read()
            if not ret:
                break
            
            height, width = frame.shape[:2]
            center_x, center_y = width // 2, height // 2
            
            # Convert to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_detection.process(rgb_frame)
            
            face_detected = False
            current_time = time.time()
            
            if results.detections:
                # Face detected
                detection = results.detections[0]
                raw_face_x, raw_face_y = get_face_center(detection, width, height)
                x1, y1, x2, y2 = get_face_bbox(detection, width, height)
                
                # Smooth the face position
                face_x = face_x_smoother.update(raw_face_x)
                face_y = face_y_smoother.update(raw_face_y)
                
                face_detected = True
                last_face_time = current_time
                searching = False
                
                # Calculate error (pixels from center)
                error_x = face_x - center_x
                error_y = face_y - center_y
                
                # Check if it's time to update servos
                if current_time - last_servo_update >= servo_update_interval:
                    in_deadzone_x = abs(error_x) <= DEAD_ZONE
                    in_deadzone_y = abs(error_y) <= DEAD_ZONE
                    
                    # LOCKED if both axes in dead zone
                    if in_deadzone_x and in_deadzone_y:
                        accumulated_pan = 0.0
                        accumulated_tilt = 0.0
                    else:
                        # Update pan if outside dead zone
                        if not in_deadzone_x:
                            pan_angle, accumulated_pan, send_pan = update_servo_axis(
                                error_x, accumulated_pan, pan_angle, PAN_MIN, PAN_MAX
                            )
                            if send_pan:
                                servos.pan(int(pan_angle))
                        else:
                            accumulated_pan = 0.0
                        
                        # Update tilt if outside dead zone
                        if not in_deadzone_y:
                            tilt_angle, accumulated_tilt, send_tilt = update_servo_axis(
                                error_y, accumulated_tilt, tilt_angle, TILT_MIN, TILT_MAX
                            )
                            if send_tilt:
                                servos.tilt(int(tilt_angle))
                        else:
                            accumulated_tilt = 0.0
                    
                    last_servo_update = current_time
                
                # Determine status
                locked = abs(error_x) <= DEAD_ZONE and abs(error_y) <= DEAD_ZONE
                status = "LOCKED ✓" if locked else "TRACKING"
                status_color = COLOR_LOCKED if locked else COLOR_TRACKING
                
                # Draw tracking visualization
                draw_tracking_overlay(frame, face_x, face_y, x1, y1, x2, y2, error_x, error_y,
                                    pan_angle, tilt_angle, status, status_color)
            
            # SEARCH MODE
            elif current_time - last_face_time > SEARCH_DELAY:
                if not searching:
                    searching = True
                    print("\nSearching for face...")
                    face_x_smoother.reset()
                    face_y_smoother.reset()
                
                if current_time - last_search_update >= search_update_interval:
                    pan_angle += SEARCH_STEP * search_direction
                    
                    if pan_angle >= SEARCH_PAN_MAX:
                        pan_angle = SEARCH_PAN_MAX
                        search_direction = -1
                        search_tilt_index = (search_tilt_index + 1) % len(SEARCH_TILT_POSITIONS)
                        tilt_angle = SEARCH_TILT_POSITIONS[search_tilt_index]
                    elif pan_angle <= SEARCH_PAN_MIN:
                        pan_angle = SEARCH_PAN_MIN
                        search_direction = 1
                    
                    servos.move(int(pan_angle), int(tilt_angle))
                    last_search_update = current_time
                
                draw_overlay(frame, pan_angle, tilt_angle, "SEARCHING...", COLOR_SEARCHING)
            
            else:
                draw_overlay(frame, pan_angle, tilt_angle, "WAITING...", COLOR_WAITING)
            
            # Show frame
            cv2.imshow(WINDOW_TITLE, frame)
            
            # Check for ESC
            if cv2.waitKey(1) & 0xFF == 27:
                break
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        face_detection.close()
        servos.close()
        print("\nFace tracker stopped")


if __name__ == "__main__":
    main()

