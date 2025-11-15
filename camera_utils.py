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
        "nvarguscamerasrc sensor-id=%d ! "
        "video/x-raw(memory:NVMM), "
        "width=(int)%d, height=(int)%d, "
        "format=(string)NV12, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
        % (
            sensor_id,
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
        )
    )

