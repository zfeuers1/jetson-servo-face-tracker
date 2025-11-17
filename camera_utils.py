"""
Camera utilities for IMX477 on Jetson Orin
"""

def gstreamer_pipeline(
    sensor_id=0,
    capture_width=1920,
    capture_height=1080,
    display_width=1920,
    display_height=1080,
    framerate=30,
    flip_method=0,
):
    """
    Create GStreamer pipeline for IMX477 camera
    
    Args:
        sensor_id: Camera ID (0 for first camera)
        capture_width: Sensor width
        capture_height: Sensor height
        display_width: Output width
        display_height: Output height
        framerate: Framerate
        flip_method: 0=none, 1=ccw90, 2=180, 3=cw90, 4=horizontal, 5=vertical
    
    Returns:
        GStreamer pipeline string for use with cv2.VideoCapture
    """
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM), width=(int){capture_width}, height=(int){capture_height}, "
        f"format=(string)NV12, framerate=(fraction){framerate}/1 ! "
        f"nvvidconv flip-method={flip_method} ! "
        f"video/x-raw, width=(int){display_width}, height=(int){display_height}, format=(string)BGRx ! "
        f"videoconvert ! video/x-raw, format=(string)BGR ! appsink"
    )

