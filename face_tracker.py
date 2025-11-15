#!/usr/bin/env python3
"""
Face Tracker - High-performance smooth tracking
Uses PD control with prediction and adaptive dead zone
Takes full advantage of Jetson Orin's capabilities
"""

import cv2
import mediapipe as mp
import time
from typing import Tuple, Optional
from collections import deque
from camera_utils import gstreamer_pipeline
from servo_controller_v2 import ServoController

# MediaPipe face detection
mp_face_detection = mp.solutions.face_detection

# Tracking parameters - SIMPLE is better!
DEAD_ZONE = 150      # Pixels - "close enough" zone (servo precision limit)
MIN_MOVE = 5           # Minimum degrees (servo dead band)
GAIN = 0.02            # How many degrees per pixel of error
UPDATE_RATE = 10       # Hz - servo update frequency
SMOOTHING = 0.7        # Face position smoothing (higher = more responsive)

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
        self.alpha = alpha  # Smoothing factor (0-1)
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


def main():
    """Main face tracker with PD control"""
    
    print("=" * 60)
    print("Face Tracker - SIMPLE Mode (No Oscillation)")
    print("=" * 60)
    print()
    print("Controls:")
    print("  ESC - Exit")
    print()
    print("Features:")
    print(f"  • 60fps camera")
    print(f"  • {UPDATE_RATE}Hz servo updates")
    print(f"  • Simple proportional control")
    print(f"  • Dead zone: {DEAD_ZONE}px")
    print()
    
    # Initialize servos
    print("Initializing servos...")
    try:
        servos = ServoController(pan_center=90, tilt_center=95)
    except Exception as e:
        print(f"✗ Failed to initialize servos: {e}")
        return
    
    # Start position
    pan_angle = 90.0
    tilt_angle = 45.0
    servos.move(int(pan_angle), int(tilt_angle))
    print(f"✓ Starting position: Pan={pan_angle:.0f}° Tilt={tilt_angle:.0f}°")
    
    # Create GStreamer pipeline - 1080p @ 60fps
    pipeline = gstreamer_pipeline(
        sensor_id=0,
        capture_width=1920,
        capture_height=1080,
        display_width=1920,
        display_height=1080,
        framerate=60,
        flip_method=0,
    )
    
    # Open camera
    print("Opening camera...")
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    
    if not cap.isOpened():
        print("✗ Failed to open camera")
        servos.close()
        return
    
    print("✓ Camera opened at 1080p60")
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
    last_servo_update = time.time()
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
                    # Check if we're "close enough" (inside dead zone)
                    in_deadzone_x = abs(error_x) <= DEAD_ZONE
                    in_deadzone_y = abs(error_y) <= DEAD_ZONE
                    
                    # COMPLETE STOP if both X and Y are inside dead zone
                    if in_deadzone_x and in_deadzone_y:
                        # LOCKED - do absolutely nothing!
                        accumulated_pan = 0.0
                        accumulated_tilt = 0.0
                    else:
                        # Outside dead zone - need to track
                        
                        # PAN: only adjust if outside dead zone
                        if not in_deadzone_x:
                            move_pan = -error_x * GAIN
                            accumulated_pan += move_pan
                            
                            # Only send command if accumulated error exceeds servo dead band
                            if abs(accumulated_pan) >= MIN_MOVE:
                                pan_angle += accumulated_pan
                                pan_angle = clamp(pan_angle, PAN_MIN, PAN_MAX)
                                servos.pan(int(pan_angle))
                                accumulated_pan = 0.0
                        else:
                            accumulated_pan = 0.0
                        
                        # TILT: only adjust if outside dead zone
                        if not in_deadzone_y:
                            move_tilt = -error_y * GAIN
                            accumulated_tilt += move_tilt
                            
                            # Only send command if accumulated error exceeds servo dead band
                            if abs(accumulated_tilt) >= MIN_MOVE:
                                tilt_angle += accumulated_tilt
                                tilt_angle = clamp(tilt_angle, TILT_MIN, TILT_MAX)
                                servos.tilt(int(tilt_angle))
                                accumulated_tilt = 0.0
                        else:
                            accumulated_tilt = 0.0
                    
                    last_servo_update = current_time
                
                # Visualization
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                cv2.circle(frame, (int(face_x), int(face_y)), 10, (0, 255, 0), -1)
                cv2.line(frame, (center_x, center_y), (int(face_x), int(face_y)), (0, 255, 255), 2)
                
                # Draw dead zone
                cv2.rectangle(frame,
                            (center_x - DEAD_ZONE, center_y - DEAD_ZONE),
                            (center_x + DEAD_ZONE, center_y + DEAD_ZONE),
                            (100, 100, 255), 2)
                
                # Status
                if abs(error_x) <= DEAD_ZONE and abs(error_y) <= DEAD_ZONE:
                    status = "LOCKED ✓"
                    status_color = (0, 255, 0)
                else:
                    status = "TRACKING"
                    status_color = (0, 200, 255)
            
            # SEARCH MODE
            elif current_time - last_face_time > SEARCH_DELAY:
                if not searching:
                    searching = True
                    print("\nSearching for face...")
                    face_x_smoother.reset()
                    face_y_smoother.reset()
                
                if current_time - last_servo_update >= servo_update_interval:
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
                    last_servo_update = current_time
                
                status = "SEARCHING..."
                status_color = (255, 165, 0)
            
            else:
                status = "WAITING..."
                status_color = (150, 150, 150)
            
            # Draw center crosshair
            cv2.line(frame, (center_x - 30, center_y), (center_x + 30, center_y), (255, 0, 0), 3)
            cv2.line(frame, (center_x, center_y - 30), (center_x, center_y + 30), (255, 0, 0), 3)
            
            # Display info
            cv2.putText(frame, status, (10, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, status_color, 3)
            
            servo_text = f"Pan:{pan_angle:.1f}°  Tilt:{tilt_angle:.1f}°"
            cv2.putText(frame, servo_text, (10, height - 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            info_text = f"Simple Control | {UPDATE_RATE}Hz | Dead zone: {DEAD_ZONE}px | Gain: {GAIN}"
            cv2.putText(frame, info_text, (10, height - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)
            
            # Show frame
            cv2.imshow("Face Tracker - Simple Mode", frame)
            
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

