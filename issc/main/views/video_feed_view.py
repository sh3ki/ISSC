import cv2
# Silence verbose OpenCV logs (e.g., DirectShow warnings)
try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
except Exception:
    pass
import os
import numpy as np
from django.http import StreamingHttpResponse, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from threading import Thread
from queue import Queue
import time
import signal
import sys
from django.template import loader
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
try:
    import tensorflow as tf
except Exception:
    tf = None
import json
import shutil

# Fix CUDA memory errors with these environment variables
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
os.environ['TF_FORCE_GPU_ALLOWED_GROWTH'] = 'true'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TensorFlow warnings
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'  # Help with memory fragmentation

from dotenv import load_dotenv
load_dotenv()

from ..models import AccountRegistration, IncidentReport, VehicleRegistration, FaceLogs
import subprocess
from django.conf import settings
import re

# Initialize GPU status dictionary to monitor GPU usage across frameworks
gpu_status = {
    'tensorflow': False,
    'pytorch': False,
    'opencv_cuda': False
}

# Check and configure GPU (TensorFlow optional)
print("Checking GPU availability for TensorFlow:")
if tf is not None and hasattr(tf, "config"):
    try:
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            try:
                for gpu in gpus:
                    # set_memory_growth might be under experimental in older TFs
                    if hasattr(tf, "config") and hasattr(tf.config, "experimental") and hasattr(tf.config.experimental, "set_memory_growth"):
                        tf.config.experimental.set_memory_growth(gpu, True)
                print(f"TensorFlow using GPU: {getattr(tf.test, 'gpu_device_name', lambda: 'unknown')()}")
                gpu_status['tensorflow'] = True
            except Exception as e:
                print(f"GPU configuration error: {e}")
        else:
            print("TensorFlow GPU not available, running on CPU")
    except Exception as e:
        print(f"TensorFlow GPU initialization skipped: {e}")
else:
    print("TensorFlow not installed or missing GPU APIs; skipping")

# Check PyTorch GPU
try:
    import torch
    if torch.cuda.is_available():
        print(f"PyTorch using GPU: {torch.cuda.get_device_name(0)}")
        gpu_status['pytorch'] = True
        
        # Clean up CUDA memory at start
        torch.cuda.empty_cache()
    else:
        print("PyTorch GPU not available")
except ImportError:
    print("PyTorch not installed")

# Configure OpenCV for CUDA
print("Configuring OpenCV with CUDA:")
cv2.setUseOptimized(True)
try:
    # Check if CUDA is available for OpenCV
    count = cv2.cuda.getCudaEnabledDeviceCount()
    if count > 0:
        cv2.cuda.setDevice(0)
        print(f"OpenCV CUDA enabled with {count} device(s)")
        gpu_status['opencv_cuda'] = True
    else:
        print("OpenCV CUDA not available - standard OpenCV will be used")
except:
    print("OpenCV CUDA support not built in this version")

print(f"GPU initialization complete: {gpu_status}")

from ..computer_vision.face_matching import FaceMatcher
from ..computer_vision.face_enrollment import FaceEnrollment

# Initialize face detector - use GPU via PyTorch for best performance
face_detector = FaceEnrollment(device='cuda')

# Initialize face matcher - enable GPU for PyTorch operations
matcher = FaceMatcher(use_gpu=True)  
matcher.load_embeddings()  # Load all face embeddings from database

SAVE_DIR = 'recordings'
os.makedirs(SAVE_DIR, exist_ok=True)

# Video settings - optimize for stability and performance
FRAME_WIDTH, FRAME_HEIGHT = 560, 420  # Slightly lower resolution for better performance
FPS = 20  # Reduced for better stability
VIDEO_FORMAT = "XVID"
FRAME_SKIP = 4  # INCREASED to process fewer frames for better performance

# Initialize haarcascade as a fallback face detector (reliable when deep learning fails)
cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(cascade_path)

# Error rate limiting variables
last_error_time = 0
error_cooldown = 5  # seconds

# Camera auto-start can be noisy on Windows; control via env FLAG
# Set CAMERA_AUTO_START=1 to probe/open physical cameras on server start.
# Default is disabled to avoid DShow/DSH spam and open cameras on-demand only.
AUTO_START_CAMERAS = os.getenv('CAMERA_AUTO_START', '0').lower() in ('1', 'true', 'yes')

# Optional: choose preferred backend on Windows (dshow | msmf | any)
PREFERRED_BACKEND = os.getenv('OPENCV_BACKEND', 'dshow').lower()
_BACKEND_MAP = {
    'dshow': getattr(cv2, 'CAP_DSHOW', 0),
    'msmf': getattr(cv2, 'CAP_MSMF', 0),
    'any': 0,
}

# Initialize cameras with improved detection
def detect_cameras():
    """Detect available cameras and return a dictionary of working camera objects
    This function will detect all physical cameras and return them by their physical index.
    Assignment to logical cameras happens in initialize_live_feed_cameras().
    """
    MAX_CAMERAS_TO_TRY = 3  # Check for 3 cameras to include physical index 2 where Rapoo is located
    available_cameras = {}
    
    print("🔍 Detecting cameras for live feed...")
    print("📹 Scanning for all available physical cameras...")
    print("📹 Will assign: Frontend Camera 0 = Acer HD (physical 1), Frontend Camera 1 = Rapoo (physical 2)")
    
    for i in range(MAX_CAMERAS_TO_TRY):
        camera_name = "Acer HD user-facing camera" if i == 1 else "Rapoo camera" if i == 2 else f"Camera {i}"
        print(f"🔍 Testing Camera {i} ({camera_name})...")
        
        # Special handling for Rapoo camera (physical camera 2)
        if i == 2:
            print(f"🔧🔧🔧 === RAPOO CAMERA DETECTION START === 🔧🔧🔧")
            print(f"🎯 Attempting to detect Rapoo camera on physical index {i}")
        
        try:
            # Try multiple backends for better compatibility - more extensive for Rapoo
            if i == 2:  # Rapoo camera needs more backend options
                backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_V4L2, cv2.CAP_ANY, 0]
                print(f"🔧 RAPOO: Trying {len(backends)} different backends...")
            else:
                backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, 0]
            
            cap = None
            for backend_idx, backend in enumerate(backends):
                try:
                    if i == 2:
                        print(f"🎯 RAPOO Backend {backend_idx+1}/{len(backends)}: Testing backend {backend}")
                    
                    tmp = cv2.VideoCapture(i, backend)
                    
                    if i == 2:
                        print(f"🎯 RAPOO: VideoCapture created, isOpened() = {tmp.isOpened()}")
                    
                    if tmp.isOpened():
                        # Give camera time to initialize (especially important for Rapoo)
                        if i == 2:
                            print(f"🎯 RAPOO: Camera opened, waiting 0.5s for initialization...")
                            time.sleep(0.5)
                        
                        # Test if we can actually read a frame
                        ret, test_frame = tmp.read()
                        
                        if i == 2:
                            print(f"🎯 RAPOO: Frame read test - ret={ret}, frame_valid={test_frame is not None and test_frame.shape[0] > 0 if test_frame is not None else False}")
                        
                        if ret and test_frame is not None and test_frame.shape[0] > 0:
                            cap = tmp
                            if i == 2:
                                print(f"✅✅✅ RAPOO SUCCESS: Camera {i} opened with backend {backend}! ✅✅✅")
                            else:
                                print(f"   ✅ Camera {i} opened with backend {backend}")
                            break
                        else:
                            if i == 2:
                                print(f"🚨 RAPOO: Frame read failed, trying next backend...")
                            tmp.release()
                    else:
                        if i == 2:
                            print(f"🚨 RAPOO: Camera failed to open with backend {backend}")
                        tmp.release()
                except Exception as e:
                    if i == 2:
                        print(f"🚨 RAPOO Backend {backend} failed: {e}")
                    else:
                        print(f"   ❌ Backend {backend} failed: {e}")
                    continue
            
            if cap is None:
                if i == 2:
                    print(f"🚨🚨🚨 RAPOO DETECTION FAILED: Camera {i} ({camera_name}) not available on any backend 🚨🚨🚨")
                    print(f"🔧 RAPOO: This means the Rapoo camera is not being detected by Windows/OpenCV")
                    print(f"🔧 RAPOO: Check if camera is connected and not used by another application")
                else:
                    print(f"   ❌ Camera {i} ({camera_name}) not available on any backend")
                continue
            if cap.isOpened():
                # Test camera by reading multiple frames to ensure stability
                test_success = 0
                frame_test_failed = False
                streaming_test_passed = False
                
                try:
                    # Add special debug for Rapoo camera (physical camera 2)
                    if i == 2:
                        print(f"🔧 === RAPOO CAMERA TESTING START ===")
                        print(f"🎬 Testing physical camera {i} for Camera 0 Rapoo assignment...")
                        print(f"🎯 RAPOO: Camera object type: {type(cap)}")
                        print(f"🎯 RAPOO: Camera resolution: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
                    
                    # First test: Basic frame reading with enhanced Rapoo debugging
                    for test_frame in range(3):
                        ret, frame = cap.read()
                        if i == 2:  # Rapoo camera debug
                            frame_info = "None"
                            if frame is not None:
                                frame_info = f"{frame.shape[1]}x{frame.shape[0]} ({frame.dtype})"
                            print(f"📹 RAPOO Basic Test {test_frame+1}/3: ret={ret}, frame={frame_info}")
                        if ret and frame is not None and frame.shape[0] > 0 and frame.shape[1] > 0:
                            test_success += 1
                        time.sleep(0.2 if i == 2 else 0.1)  # More time for Rapoo between reads
                    
                    # Second test: Streaming stability test (similar to actual usage)
                    # SKIP for Rapoo camera (index 2) - NVIDIA Broadcast doesn't like extensive testing
                    if test_success >= 2:
                        if i == 2:
                            # For Rapoo camera: Skip streaming test, just configure and accept
                            print(f"🎯 RAPOO: Skipping streaming test (NVIDIA Broadcast is sensitive)")
                            cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
                            cap.set(cv2.CAP_PROP_FPS, FPS)
                            streaming_test_passed = True
                            print(f"✅ RAPOO accepted based on basic tests (3/3 passed)")
                        else:
                            # For other cameras: Do full streaming test
                            cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
                            cap.set(cv2.CAP_PROP_FPS, FPS)
                            
                            # Test continuous reading for streaming simulation
                            streaming_success = 0
                            for stream_test in range(5):  # More rigorous test
                                ret, frame = cap.read()
                                if ret and frame is not None and frame.shape[0] > 0 and frame.shape[1] > 0:
                                    streaming_success += 1
                                time.sleep(0.05)  # Simulate actual streaming intervals
                            
                            if streaming_success >= 4:  # Must pass at least 4/5 streaming tests
                                streaming_test_passed = True
                                
                except Exception as frame_error:
                    print(f"Camera {i} frame test failed: {frame_error}")
                    frame_test_failed = True
                
                if not frame_test_failed and test_success >= 2 and streaming_test_passed:
                    camera_name = "Acer HD user-facing camera" if i == 1 else "Rapoo camera" if i == 2 else f"Camera {i}"
                    print(f"✅ Camera {i}: {camera_name} is working (passed {test_success}/3 basic tests + streaming test)")
                    available_cameras[i] = cap
                else:
                    reason = []
                    if frame_test_failed:
                        reason.append("frame test failed")
                    if test_success < 2:
                        reason.append(f"basic test failed ({test_success}/3)")
                    if not streaming_test_passed:
                        reason.append("streaming test failed")
                    print(f"Camera {i} rejected: {', '.join(reason)}")
                    cap.release()
        except Exception as e:
            print(f"Error detecting camera {i}: {e}")
    
    print(f"Found {len(available_cameras)} working cameras")
    
    # Special Rapoo camera recovery attempt if not detected
    if 2 not in available_cameras:
        print(f"🔧 RAPOO RECOVERY: Physical camera 2 (Rapoo) not detected, trying recovery methods...")
        
        # Recovery method 1: Try with longer initialization time
        print(f"🔧 RAPOO RECOVERY 1: Trying with extended initialization time...")
        try:
            recovery_cap = cv2.VideoCapture(2, cv2.CAP_DSHOW)
            if recovery_cap.isOpened():
                print(f"🔧 RAPOO RECOVERY: Camera opened, waiting 2 seconds for full initialization...")
                time.sleep(2)  # Give more time
                
                # Try reading multiple frames to "warm up" the camera
                for warm_up in range(10):
                    ret, frame = recovery_cap.read()
                    print(f"🔧 RAPOO WARMUP {warm_up+1}/10: ret={ret}")
                    if ret and frame is not None:
                        print(f"✅ RAPOO RECOVERY SUCCESS: Camera working after warmup!")
                        available_cameras[2] = recovery_cap
                        break
                    time.sleep(0.1)
                
                if 2 not in available_cameras:
                    recovery_cap.release()
            
        except Exception as e:
            print(f"🚨 RAPOO RECOVERY 1 failed: {e}")
        
        # Recovery method 2: Try different camera indices (sometimes cameras shift)
        if 2 not in available_cameras:
            print(f"🔧 RAPOO RECOVERY 2: Trying camera indices 0, 3-5 in case Rapoo shifted...")
            for alt_index in [0, 3, 4, 5]:
                try:
                    alt_cap = cv2.VideoCapture(alt_index, cv2.CAP_DSHOW)
                    if alt_cap.isOpened():
                        ret, frame = alt_cap.read()
                        if ret and frame is not None:
                            print(f"✅ RAPOO FOUND: Camera detected at index {alt_index} instead of 2!")
                            available_cameras[2] = alt_cap  # Assign to physical index 2
                            break
                    alt_cap.release()
                except Exception as e:
                    print(f"🔧 RAPOO RECOVERY: Index {alt_index} failed: {e}")
    
    # If no cameras were found, create a dummy camera
    if not available_cameras:
        print("No working cameras found, using dummy camera")
        available_cameras[0] = None
        
    return available_cameras

def get_available_cameras_info():
    """
    Get information about available cameras for dropdown selection with real device names
    WITHOUT opening/testing the cameras (fast method)
    
    IMPORTANT: Maps PowerShell camera names to actual OpenCV camera indices
    """
    print("Getting available cameras info for dropdown (fast method)...")
    camera_info = []
    
    try:
        import subprocess
        import json
        
        # Use PowerShell to get camera names - NO camera opening!
        powershell_command = """
        Get-PnpDevice -Class Camera,Image | 
        Where-Object {$_.Status -eq 'OK'} | 
        Select-Object FriendlyName, InstanceId | 
        ConvertTo-Json
        """
        
        result = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            devices = json.loads(result.stdout)
            
            # Handle single device (not a list)
            if isinstance(devices, dict):
                devices = [devices]
            
            # FIXED MAPPING: Match camera names to actual OpenCV indices
            # Based on testing with test_camera_mapping.py:
            # PowerShell Index 0 = "ACER HD User Facing" → OpenCV Camera 1
            # PowerShell Index 1 = "rapoo camera" → OpenCV Camera 0
            # The indices are SWAPPED!
            
            for idx, device in enumerate(devices):
                friendly_name = device.get('FriendlyName', f'Camera {idx}')
                
                # Map PowerShell index to correct OpenCV index (SWAPPED!)
                if idx == 0:
                    opencv_index = 1  # ACER is at OpenCV index 1
                elif idx == 1:
                    opencv_index = 0  # Rapoo is at OpenCV index 0
                else:
                    opencv_index = idx  # Keep other cameras as-is
                
                camera_info.append({
                    'id': opencv_index,
                    'name': friendly_name,
                    'status': 'Available'
                })
                print(f"📷 Camera {opencv_index}: {friendly_name}")
        else:
            print("⚠️ PowerShell query returned no cameras, falling back to default list")
            # Fallback: provide default camera indices
            camera_info = [
                {'id': 0, 'name': 'Camera 0', 'status': 'Available'},
                {'id': 1, 'name': 'Camera 1', 'status': 'Available'},
            ]
    
    except Exception as e:
        print(f"❌ Error getting camera info: {e}")
        # Fallback on error
        camera_info = [
            {'id': 0, 'name': 'Camera 0', 'status': 'Available'},
            {'id': 1, 'name': 'Camera 1', 'status': 'Available'},
        ]
    
    print(f"✅ Available cameras for selection: {camera_info}")
    return camera_info

# Page-specific camera initialization - cameras only open when needed
cameras = {}  # Empty by default - cameras initialized on-demand
frame_queues = {}
video_writers = {}
face_cameras = {}  # Separate cameras for face enrollment
face_frame_queues = {}

# Initialize dummy cameras by default
def initialize_dummy_cameras():
    """Initialize dummy cameras for when no page is accessing cameras"""
    global cameras, frame_queues
    cameras = {0: None}
    frame_queues = {0: Queue(maxsize=2)}

# Initialize dummy state
initialize_dummy_cameras()
face_cam_id = 0
frame_counts = {i: 0 for i in cameras}

running = True
recording = False

# MOVED HERE - Now cameras is defined before using it
# Initialize display states with anti-flickering properties
display_states = {i: {
    "face_count": 0, 
    "previous_face_count": 0,  # Track previous count to avoid flickering
    "last_update": time.time(),
    "face_locations": [],       # Store face locations
    "face_matches": [],         # Store match results
    "stable_since": time.time(),  # Track stability time
    "update_needed": False      # Flag to control updates
} for i in cameras}

# Global stable no-signal frame to prevent flickering - single instance
_stable_no_signal_frame = None

def generate_no_signal_frame():
    """Returns THE SAME stable 'No Signal' frame instance to completely prevent flickering."""
    global _stable_no_signal_frame
    
    # Create the frame only once
    if _stable_no_signal_frame is None:
        width, height = FRAME_WIDTH, FRAME_HEIGHT
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Use solid dark background - no gradients, no animation
        frame[:] = (40, 40, 40)  # Dark gray background
        
        # Add simple border
        cv2.rectangle(frame, (0, 0), (width, height), (60, 60, 60), 2)
        
        # Static "NO SIGNAL" text - perfectly centered
        text_x = width // 2 - 120
        text_y = height // 2 - 20
        cv2.putText(frame, "NO SIGNAL", (text_x, text_y), cv2.FONT_HERSHEY_DUPLEX, 1.5, (200, 200, 200), 3, cv2.LINE_AA)
        
        # Static warning icon
        icon_center_x = width // 2
        icon_center_y = height // 2 + 60
        cv2.circle(frame, (icon_center_x, icon_center_y), 25, (100, 100, 100), -1)
        cv2.putText(frame, "!", (icon_center_x - 8, icon_center_y + 10), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (200, 200, 200), 3, cv2.LINE_AA)
        
        _stable_no_signal_frame = frame
        print("🖼️ Created single stable NO SIGNAL frame to prevent flickering")
    
    # Return the EXACT SAME frame reference - no copying to prevent any changes
    return _stable_no_signal_frame

def capture_frames(camera_id):
    """Captures frames with robust error handling and stable no-signal display"""
    global cameras, recording, display_states
    
    camera_name = "Acer HD user-facing camera" if camera_id == 0 else "Rapoo camera" if camera_id == 1 else f"Camera {camera_id}"
    
    # If camera is None, this is a dummy camera
    if cameras[camera_id] is None:
        print(f"📵 Camera {camera_id} ({camera_name}) showing ANTI-FLICKER NO SIGNAL")
        # Get the single stable frame instance once
        stable_frame = generate_no_signal_frame()
        while running:
            if not frame_queues[camera_id].full():
                # Use the EXACT SAME frame reference - no copying, no modifications
                frame_queues[camera_id].put(stable_frame)
            time.sleep(1/FPS)
        return
        
    cap = cameras[camera_id]
    consecutive_failures = 0
    max_failures = 10
    
    while running:
        try:
            success, frame = cap.read()
            
            if not success or frame is None:
                consecutive_failures += 1
                frame = generate_no_signal_frame()
                
                # If too many failures, try to reinitialize camera
                if consecutive_failures > max_failures:
                    print(f"🔄 Reinitializing camera {camera_id} after {consecutive_failures} failures")
                    
                    cap.release()
                    time.sleep(1)  # Wait a bit before attempting to reconnect
                    
                    # Reinitialize with correct physical index
                    # Camera 0 = Physical 1 (Acer HD), Camera 1 = Physical 2 (Rapoo)
                    physical_cam_index = 1 if camera_id == 0 else 2 if camera_id == 1 else camera_id
                    cap = cv2.VideoCapture(physical_cam_index, cv2.CAP_DSHOW)
                    
                    if not cap.isOpened():
                        if camera_id == 1:
                            print(f"❌ Failed to reinitialize RAPOO camera {camera_id} (physical {physical_cam_index})")
                        else:
                            print(f"Failed to reinitialize camera {camera_id}")
                        cameras[camera_id] = None
                        return
                    
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
                    cap.set(cv2.CAP_PROP_FPS, FPS)
                    cameras[camera_id] = cap
                    consecutive_failures = 0
                    
                    if camera_id == 1:
                        print(f"✅ RAPOO camera {camera_id} reinitialized successfully")
            else:
                consecutive_failures = 0  # Reset counter on success
            
            # Only process every FRAME_SKIP frames to reduce CPU/GPU load
            frame_counts[camera_id] += 1
            
            # Periodically clean up CUDA memory to prevent fragmentation
            if frame_counts[camera_id] % 100 == 0 and torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # Process face detection for all cameras
            if frame_counts[camera_id] % FRAME_SKIP == 0:
                processed_frame = process_with_model(frame, camera_id)
                # Update display state with processed frame data
                if 'face_count' in display_states[camera_id]:
                    # Only update if there was a significant change, prevents flickering
                    new_count = display_states[camera_id].get('new_face_count', 0)
                    current_count = display_states[camera_id]['face_count']
                    
                    # Anti-flickering: Only update after consistent detections
                    if new_count != current_count:
                        if display_states[camera_id].get('pending_count', -1) != new_count:
                            # First time seeing this count, start tracking it
                            display_states[camera_id]['pending_count'] = new_count
                            display_states[camera_id]['pending_since'] = time.time()
                        elif time.time() - display_states[camera_id]['pending_since'] > 0.5:
                            # Count has been stable for 0.5 seconds, accept the change
                            display_states[camera_id]['face_count'] = new_count
                            display_states[camera_id]['previous_face_count'] = current_count
                            display_states[camera_id]['update_needed'] = True
                    else:
                        # Count matches, clear pending count
                        display_states[camera_id]['pending_count'] = -1
                frame = processed_frame
            else:
                # For frames we're not processing, still draw face boxes and overlay text
                frame = add_overlay_text(frame, camera_id)
                frame = draw_face_boxes(frame, camera_id)
            
            if not frame_queues[camera_id].full():
                frame_queues[camera_id].put(frame)

            # Make sure recording happens if enabled
            if recording and camera_id in video_writers:
                if video_writers[camera_id] and video_writers[camera_id].isOpened():
                    video_writers[camera_id].write(frame)
                elif recording:
                    # If writer isn't working but recording is on, try to reinitialize
                    initialize_video_writers()

        except Exception as e:
            consecutive_failures += 1
            
            # Only print error every 30 failures to avoid spam
            if consecutive_failures % 30 == 1:
                print(f"Error in camera {camera_id}: {e} (failed {consecutive_failures} times)")
            
            if not frame_queues[camera_id].full():
                frame_queues[camera_id].put(generate_no_signal_frame())
            
            # If camera has failed too many times, disable it
            if consecutive_failures > max_failures * 3:
                print(f"Camera {camera_id} has failed {consecutive_failures} times. Disabling.")
                cameras[camera_id] = None
                return
                
            time.sleep(0.5)  # Add delay to avoid rapid error loops
        
        # Proper frame rate control
        time.sleep(max(1/FPS - 0.01, 0.01))

def add_overlay_text(frame, camera_id):
    """Adds consistent overlay text to every frame"""
    # Copy frame to avoid modifying the original
    display_frame = frame.copy()
    
    # Camera ID - always show this
    cv2.putText(display_frame, f"CAM {camera_id}", (20, 40), 
              cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    
    # Face count from persistent state - with anti-flicker
    face_count = display_states[camera_id].get('face_count', 0)
    
    # Add black background for better readability
    text = f"Faces: {face_count}"
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
    cv2.rectangle(display_frame, (20, 60), (20 + text_size[0], 85), (0, 0, 0), -1)
    
    # Draw face count text
    cv2.putText(display_frame, text, (20, 80), 
              cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    
    return display_frame

def process_with_model(frame, camera_id=None):
    """Process a frame with face detection and recognition"""
    global last_error_time, display_states

    try:
        # Make a copy to avoid reference issues
        display_frame = frame.copy()
        
        # Resize for faster processing
        small_frame = cv2.resize(frame, (320, 240))
        
        # Make array contiguous for better processing
        small_frame = np.ascontiguousarray(small_frame)
        
        face_crops = []
        face_locations = []
        
        # Try OpenCV's cascade first - it's more reliable and faster
        try:
            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
            opencv_faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(opencv_faces) > 0:
                for (x, y, w, h) in opencv_faces:
                    face_img = small_frame[y:y+h, x:x+w]
                    face_crops.append(face_img)
                    # Format to match expected face_locations: [y1, y2, x1, x2]
                    face_locations.append(np.array([y, y+h, x, x+w]))
        except Exception as e:
            pass
            
        # Only try deep learning if OpenCV didn't find any faces
        if not face_crops:
            try:
                # Extract face embeddings using the CPU-based detector
                dl_face_crops, dl_face_locations = face_detector.detect_faces(small_frame)
                if dl_face_crops and len(dl_face_crops) > 0:
                    face_crops = dl_face_crops
                    face_locations = dl_face_locations
            except Exception as e:
                current_time = time.time()
                if current_time - last_error_time > error_cooldown:
                    print(f"Deep learning face detection failed: {str(e)}")
                    last_error_time = current_time

        # Update face count in persistent state
        face_count = len(face_crops) if face_crops else 0
        if camera_id is not None:
            # Store new face count in display state
            display_states[camera_id]['new_face_count'] = face_count

            # Only update face locations if we have new detections to avoid flickering
            if face_crops and len(face_crops) > 0:
                # Store scaled face locations and initialize match results
                h, w, _ = frame.shape
                h_small, w_small, _ = small_frame.shape
                scale_x = w / w_small
                scale_y = h / h_small
                
                # Store the full-size face locations and prepare for match results
                scaled_locations = []
                match_results = []
                
                for i, face_loc in enumerate(face_locations):
                    try:
                        # Make sure face_loc is a flat array
                        if hasattr(face_loc, 'shape') and len(face_loc.shape) > 1:
                            face_loc = face_loc.flatten()
                        
                        # Extract coordinates and scale them to original frame size
                        y1 = int(face_loc[0] * scale_y)
                        y2 = int(face_loc[1] * scale_y)
                        x1 = int(face_loc[2] * scale_x)
                        x2 = int(face_loc[3] * scale_x)
                        
                        # Ensure coordinates are within frame boundaries
                        x1 = max(0, min(x1, w-1))
                        y1 = max(0, min(y1, h-1))
                        x2 = max(0, min(x2, w-1))
                        y2 = max(0, min(y2, h-1))
                        
                        # Skip if invalid dimensions
                        if x2 <= x1 or y2 <= y1:
                            continue
                            
                        # Store scaled coordinates
                        scaled_locations.append((x1, y1, x2, y2))
                        match_results.append(None)  # Will be updated with match info
                        
                        # Extract face from original frame for matching
                        face_img = frame[y1:y2, x1:x2]
                        
                        # Only attempt matching if face is valid
                        if face_img.shape[0] > 10 and face_img.shape[1] > 10:
                            try:
                                # Make face image contiguous for processing
                                face_img = np.ascontiguousarray(face_img)
                                
                                # Extract embedding - use CPU to avoid CUDA errors
                                embedding = face_detector.extract_embeddings(face_img)
                                
                                if embedding is not None:
                                    # Match against stored embeddings - now uses CPU
                                    match_id, confidence = matcher.match(embedding)
                                    
                                    # Store match result
                                    if match_id:
                                        user_info = log(match_id)
                                        match_results[i] = {
                                            'match_id': match_id,
                                            'confidence': confidence,
                                            'user_info': user_info
                                        }
                                    else:
                                        match_results[i] = {'match_id': None}
                            except Exception as e:
                                pass
                    except Exception as e:
                        pass
                        
                # Update display state atomically to prevent flickering
                if len(scaled_locations) > 0:
                    # Only update if faces are detected and stable
                    if display_states[camera_id].get('update_needed', False) or time.time() - display_states[camera_id].get('stable_since', 0) > 1.0:
                        display_states[camera_id]['face_locations'] = scaled_locations
                        display_states[camera_id]['face_matches'] = match_results
                        display_states[camera_id]['stable_since'] = time.time()
                        display_states[camera_id]['update_needed'] = False
            else:
                # If no faces detected, clear persistent face locations after a short timeout
                last_seen = display_states[camera_id].get('last_no_face', None)
                now = time.time()
                if last_seen is None:
                    display_states[camera_id]['last_no_face'] = now
                elif now - last_seen > 1.0:  # 1 second without faces
                    display_states[camera_id]['face_locations'] = []
                    display_states[camera_id]['face_matches'] = []
                    display_states[camera_id]['last_no_face'] = now  # keep updating to avoid repeated clearing
            # Reset last_no_face if faces are detected
            if face_crops and len(face_crops) > 0:
                display_states[camera_id]['last_no_face'] = None

        # Add standard overlay text to every processed frame
        display_frame = add_overlay_text(display_frame, camera_id)
        
        # Draw face boxes from persistent state to avoid flickering
        if camera_id is not None:
            display_frame = draw_face_boxes(display_frame, camera_id)
                
        return display_frame
    except Exception as e:
        current_time = time.time()
        if current_time - last_error_time > error_cooldown:
            print(f"Error in face processing: {str(e)}")
            last_error_time = current_time
        return add_overlay_text(frame, camera_id)  # Return frame with overlay even on error

def draw_face_boxes(frame, camera_id):
    """Draws face bounding boxes and labels using the persistent state data"""
    if camera_id not in display_states:
        return frame

    # Copy frame to avoid modifying the original
    display_frame = frame.copy()

    # Get face locations and matches from the persistent state
    face_locations = display_states[camera_id].get('face_locations', [])
    face_matches = display_states[camera_id].get('face_matches', [])

    # If no faces detected, return frame as-is (no bounding boxes)
    if not face_locations:
        return display_frame

    # Draw boxes for each face - more stable rendering
    for i, (x1, y1, x2, y2) in enumerate(face_locations):
        # Get match info if available
        match_info = face_matches[i] if i < len(face_matches) else None
        
        if match_info and match_info.get('match_id'):
            # AUTHORIZED USER - GREEN BOX
            # Draw solid box (more stable appearance)
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
            
            # Add second outer box for visibility
            cv2.rectangle(display_frame, (x1-2, y1-2), (x2+2, y2+2), (255, 255, 255), 1)
            
            # Display ID with black background
            id_text = f"ID: {match_info['match_id']}"
            text_size = cv2.getTextSize(id_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            cv2.rectangle(display_frame, (x1, y1-25), (x1+text_size[0], y1), (0,0,0), -1)
            cv2.putText(display_frame, id_text, (x1, y1-5), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Display name with background if user info exists
            if match_info.get('user_info'):
                user_info = match_info['user_info']
                full_name = f"{user_info.first_name} {user_info.last_name}"
                name_size = cv2.getTextSize(full_name, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                cv2.rectangle(display_frame, (x1, y2+5), (x1+name_size[0], y2+25), (0,0,0), -1)
                cv2.putText(display_frame, full_name, (x1, y2+20), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            # UNAUTHORIZED - RED BOX
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
            
            # Double bounding box for visibility - white outer box
            cv2.rectangle(display_frame, (x1-4, y1-4), (x2+4, y2+4), (255, 255, 255), 2)
            
            # Display "Unauthorized" with background
            unauth_text = "UNAUTHORIZED"
            text_size = cv2.getTextSize(unauth_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            cv2.rectangle(display_frame, (x1, y1-25), (x1+text_size[0], y1), (0,0,0), -1)
            cv2.putText(display_frame, unauth_text, (x1, y1-5), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    
    return display_frame

def initialize_video_writers():
    """Creates new video writers for each camera."""
    global video_writers
    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    new_video_writers = {}

    for cam_id in cameras:
        if cameras[cam_id] is not None:  # Skip dummy cameras
            try:
                fourcc = cv2.VideoWriter_fourcc(*VIDEO_FORMAT)
                video_path = os.path.join(SAVE_DIR, f'camera_{cam_id}_{date_str}.avi')
                new_writer = cv2.VideoWriter(video_path, fourcc, FPS, (FRAME_WIDTH, FRAME_HEIGHT))
                if new_writer.isOpened():
                    new_video_writers[cam_id] = new_writer
                    print(f"Started recording for camera {cam_id} to {video_path}")
                else:
                    print(f"Failed to create video writer for camera {cam_id}")
            except Exception as e:
                print(f"Error creating video writer for camera {cam_id}: {e}")

    video_writers = new_video_writers

def generate(camera_id):
    """Fetches frames from the queue and yields them as an HTTP stream."""
    while running:
        try:
            if not frame_queues[camera_id].empty():
                frame = frame_queues[camera_id].get()
                
                # Use better quality settings for visibility
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                yield (b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            else:
                # Small sleep to prevent CPU spinning
                time.sleep(0.01)
        except Exception as e:
            print(f"Error in generate for camera {camera_id}: {e}")
            time.sleep(0.1)  # Pause on error

def video_feed(request, camera_id):
    """Original video feed using the generate function"""
    camera_id = int(camera_id)
    return StreamingHttpResponse(generate(camera_id), content_type='multipart/x-mixed-replace; boundary=frame')

def initialize_live_feed_cameras():
    """Initialize cameras specifically for live-feed page
    Frontend Camera 0 = Acer HD (physical index 1)
    Frontend Camera 1 = Rapoo (physical index 2)
    """
    global cameras, frame_queues, display_states
    
    # First, cleanup any face enrollment cameras to avoid conflicts
    cleanup_face_enrollment_cameras()
    
    # Always try to initialize cameras when live feed is accessed
    print("🚀 Initializing cameras for live feed...")
    print("📹 Camera 0 (Frontend): Acer HD user-facing camera")
    print("📹 Camera 1 (Frontend): Rapoo camera")
    
    # Force camera detection every time
    new_cameras = detect_cameras()
    
    # Always set up camera structure for Camera 0 and Camera 1
    cameras = {}
    
    # NEW ASSIGNMENT:
    # Frontend Camera 0 = Acer HD (physical index 1)
    # Frontend Camera 1 = Rapoo (physical index 2)
    
    # Camera 0 = Acer HD camera (physical index 1)
    if new_cameras and 1 in new_cameras and new_cameras[1] is not None:
        cameras[0] = new_cameras[1]  # Physical Camera 1 → Logical Camera 0 (Acer HD)
        print("✅ Camera 0: Acer HD user-facing camera ASSIGNED (from physical camera 1)")
    else:
        cameras[0] = None
        print("❌ Camera 0: Acer HD user-facing camera NOT DETECTED")
        
    # Camera 1 = Rapoo camera (physical index 2)
    if new_cameras and 2 in new_cameras and new_cameras[2] is not None:
        cameras[1] = new_cameras[2]  # Physical Camera 2 → Logical Camera 1 (Rapoo)
        print("✅ Camera 1: Rapoo camera ASSIGNED (from physical camera 2)")
    else:
        cameras[1] = None
        print("❌ Camera 1: Rapoo camera NOT DETECTED at physical index 2")
    
    # Set up frame queues and display states for both cameras
    frame_queues = {0: Queue(maxsize=10), 1: Queue(maxsize=10)}
    display_states = {i: {
        "face_count": 0, 
        "previous_face_count": 0,
        "last_update": time.time(),
        "face_locations": [],
        "face_matches": [],
        "stable_since": time.time(),
        "update_needed": False
    } for i in [0, 1]}
    
    # Restart running flag and start capture threads for both cameras
    global running, capture_threads
    running = True
    capture_threads = []
    
    for cam_id in [0, 1]:  # Always create threads for both cameras
        thread = Thread(target=capture_frames, args=(cam_id,), daemon=True)
        thread.start()
        capture_threads.append(thread)
    
    working_cams = [i for i in [0, 1] if cameras[i] is not None]
    print(f"🎯 Live feed setup complete: {len(working_cams)} working cameras {working_cams}")

def initialize_face_enrollment_camera(selected_camera_id=None):
    """Initialize ONLY the specific selected camera for face enrollment - NO OTHER CAMERAS OPENED!"""
    global face_cameras, face_frame_queues, face_cam_id
    
    # First, cleanup any live feed cameras to avoid conflicts
    cleanup_live_feed_cameras()
    
    # Only initialize if not already done or if camera ID changed
    current_cam_id = face_cam_id if 'face_cam_id' in globals() else None
    
    if selected_camera_id is None:
        print("⚠️ No camera ID provided for face enrollment")
        face_cameras = {0: None}
        face_frame_queues = {0: Queue(maxsize=2)}
        face_cam_id = 0
        return
    
    if not face_cameras or selected_camera_id != current_cam_id:
        print(f"🎥 Initializing ONLY camera {selected_camera_id} for face enrollment...")
        
        # ONLY open the selected camera - NO OTHER CAMERAS!
        try:
            cap = cv2.VideoCapture(selected_camera_id, cv2.CAP_DSHOW)
            
            if cap.isOpened():
                # Test if we can read a frame
                ret, test_frame = cap.read()
                
                if ret and test_frame is not None and test_frame.shape[0] > 0:
                    # SUCCESS - Camera works!
                    face_cam_id = selected_camera_id
                    face_cameras = {face_cam_id: cap}
                    face_frame_queues = {face_cam_id: Queue(maxsize=10)}
                    print(f"✅ Successfully initialized camera {face_cam_id} for face enrollment")
                else:
                    # Can't read frames
                    print(f"❌ Camera {selected_camera_id} opened but can't read frames")
                    cap.release()
                    face_cameras = {selected_camera_id: None}
                    face_frame_queues = {selected_camera_id: Queue(maxsize=2)}
                    face_cam_id = selected_camera_id
            else:
                # Can't open camera
                print(f"❌ Camera {selected_camera_id} failed to open")
                face_cameras = {selected_camera_id: None}
                face_frame_queues = {selected_camera_id: Queue(maxsize=2)}
                face_cam_id = selected_camera_id
                
        except Exception as e:
            print(f"❌ Error initializing camera {selected_camera_id}: {e}")
            face_cameras = {selected_camera_id: None}
            face_frame_queues = {selected_camera_id: Queue(maxsize=2)}
            face_cam_id = selected_camera_id
    else:
        print(f"ℹ️ Camera {selected_camera_id} already initialized")

def cleanup_face_enrollment_cameras():
    """Cleanup face enrollment cameras to avoid conflicts"""
    global face_cameras, face_frame_queues
    
    if face_cameras and any(cap is not None for cap in face_cameras.values()):
        print("Cleaning up face enrollment cameras...")
        for cam_id, cap in face_cameras.items():
            if cap is not None:
                try:
                    cap.release()
                    print(f"Released face enrollment camera {cam_id}")
                except Exception as e:
                    print(f"Error releasing face enrollment camera {cam_id}: {e}")
        face_cameras = {}
        face_frame_queues = {}
        time.sleep(0.5)  # Small delay to ensure camera is fully released
        print("Face enrollment cameras cleaned up")

def cleanup_live_feed_cameras():
    """Cleanup live feed cameras to avoid conflicts"""
    global cameras, running, capture_threads, video_writers
    
    if cameras and any(cam is not None for cam in cameras.values()):
        print("Cleaning up live feed cameras...")
        
        # Stop capture threads
        running = False
        
        # Wait for threads to finish
        for thread in capture_threads:
            if thread.is_alive():
                thread.join(timeout=1)
        
        # Release all cameras
        for cam_id, cap in cameras.items():
            if cap is not None:
                try:
                    cap.release()
                    print(f"Released live feed camera {cam_id}")
                except Exception as e:
                    print(f"Error releasing live feed camera {cam_id}: {e}")
        
        # Close video writers
        for cam_id, writer in video_writers.items():
            if writer is not None:
                try:
                    writer.release()
                except Exception as e:
                    print(f"Error closing video writer for camera {cam_id}: {e}")
        
        # Reset to dummy state
        video_writers = {}
        capture_threads = []
        initialize_dummy_cameras()  # Reset to dummy cameras
        time.sleep(0.5)  # Small delay to ensure cameras are fully released
        print("Live feed cameras cleaned up")

def ensure_cameras_initialized():
    """Legacy function for backward compatibility - delegates to live feed"""
    initialize_live_feed_cameras()

@login_required(login_url='/login/')
def multiple_streams(request):
    """Original multiple streams live feed with proper camera assignment and stable no signal display"""
    print("🎬 Live Feed page accessed - initializing cameras...")
    
    # Initialize cameras specifically for live feed
    initialize_live_feed_cameras()
    
    # Start recording automatically when page loads if it's not already recording
    global recording
    if not recording:
        recording = True
        initialize_video_writers()
        print("*** AUTO STARTING RECORDING ***")
    
    user = AccountRegistration.objects.filter(username=request.user).values()
    template = loader.get_template('live-feed/live-feed.html')

    # Show ALL cameras including face camera
    all_camera_ids = list(cameras.keys())
    
    # Always show 4 boxes (or adjust this number as needed)
    # If fewer cameras available, still show 4 boxes
    num_boxes = 4
    if len(all_camera_ids) < num_boxes:
        # Pad with existing camera IDs to create placeholder boxes
        while len(all_camera_ids) < num_boxes:
            all_camera_ids.append(all_camera_ids[0] if all_camera_ids else 0)
    
    # Debug print to see cameras
    print(f"Showing cameras: {all_camera_ids}")

    context = {
        'user_role': user[0]['privilege'],
        'user_data': user[0],
        'camera_ids': all_camera_ids[:num_boxes],  # Limit to num_boxes
        'recording_status': "Recording" if recording else "Not Recording"
    }
    return HttpResponse(template.render(context, request))

def multiple_streams_legacy(request):
    """Legacy version of multiple streams (kept for compatibility)"""
    # Initialize cameras specifically for live feed
    initialize_live_feed_cameras()
    
    # Start recording automatically when page loads if it's not already recording
    global recording
    if not recording:
        recording = True
        initialize_video_writers()
        print("*** AUTO STARTING RECORDING ***")
    
    user = AccountRegistration.objects.filter(username=request.user).values()
    template = loader.get_template('live-feed/live-feed.html')

    # Show ALL cameras including face camera
    all_camera_ids = list(cameras.keys())
    
    # Debug print to see cameras
    print(f"Showing cameras: {all_camera_ids}")

    context = {
        'user_role': user[0]['privilege'],
        'user_data': user[0],
        'camera_ids': all_camera_ids,
        'recording_status': "Recording" if recording else "Not Recording"
    }
    return HttpResponse(template.render(context, request))

def start_record(request):
    global recording
    if recording:
        return redirect('multiple_streams')
    else:
        recording = True
        initialize_video_writers()
        print("*** MANUALLY STARTED RECORDING ***")
        return redirect('multiple_streams')

def stop_record(request):
    global recording
    if recording:
        recording = False
        global video_writers

        # Release current video writers
        for cam_id in video_writers:
            if video_writers[cam_id] and video_writers[cam_id].isOpened():
                video_writers[cam_id].release()
                print(f"Stopped recording for camera {cam_id}")
        
        # Do NOT convert recordings to MP4 here
        # recordings_dir = os.path.join(settings.BASE_DIR, 'recordings')
        # reencode_avi_to_mp4(recordings_dir)

        return redirect('multiple_streams')
    else:
        return redirect('multiple_streams')

def check_cams(request):
    """Returns the number of available cameras."""
    return HttpResponse(str(len(cameras)))

def reset_recordings(request):
    """Stops current video recording and starts a new one for each camera."""
    global recording, video_writers

    # Release current video writers
    for cam_id in video_writers:
        if video_writers[cam_id] and video_writers[cam_id].isOpened():
            video_writers[cam_id].release()
    
    # Do NOT convert recordings to MP4 here
    # recordings_dir = os.path.join(settings.BASE_DIR, 'recordings')
    # reencode_avi_to_mp4(recordings_dir)
    
    # Start new recordings
    if recording:
        initialize_video_writers()

    return redirect('recording_archive')

def recording_archive(request):
    """Renders the recording archive page with available recordings."""
    user = AccountRegistration.objects.filter(username=request.user).values()

    # Define the recordings directory
    recordings_dir = os.path.join(settings.BASE_DIR, 'recordings')

    # Look for both AVI and MP4 files
    filename_pattern_mp4 = re.compile(r"camera_(\d+)_(\d+)-(\d+)-(\d+)_(\d+-\d+-\d+)\.mp4")
    filename_pattern_avi = re.compile(r"camera_(\d+)_(\d+)-(\d+)-(\d+)_(\d+-\d+-\d+)\.avi")

    categorized_recordings = {}

    if os.path.exists(recordings_dir):
        for filename in os.listdir(recordings_dir):
            match = filename_pattern_mp4.match(filename) or filename_pattern_avi.match(filename)
            if match:
                cam_id, year, month, day, time = match.groups()

                # Structure: {camera_id: {year: {month: {day: [filenames]}}}}
                categorized_recordings.setdefault(cam_id, {}).setdefault(year, {}).setdefault(month, {}).setdefault(day, []).append(filename)

    template = loader.get_template('live-feed/recording_arcihve.html')
    context = {
        'user_role': user[0]['privilege'],
        'user_data': user[0],
        'categorized_recordings': categorized_recordings,  # Pass the structured data
    }

    return HttpResponse(template.render(context, request))

def handle_exit(signum, frame):
    """Handles graceful shutdown on Ctrl + C."""
    global running
    running = False
    print("\nShutting down... Closing video files.")

    for cam_id in cameras:
        if cameras[cam_id] is not None and cameras[cam_id].isOpened():
            cameras[cam_id].release()
        if cam_id in video_writers and video_writers[cam_id] and video_writers[cam_id].isOpened():
            video_writers[cam_id].release()
    
    sys.exit(0)

# Register signal handler for Ctrl + C
signal.signal(signal.SIGINT, handle_exit)

def reencode_avi_to_mp4(directory):
    """Searches for all .avi files in the specified directory, converts them to .mp4 using ffmpeg, and deletes the original .avi files."""
    
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist.")
        return

    for filename in os.listdir(directory):
        if filename.endswith(".avi"):
            avi_path = os.path.join(directory, filename)
            mp4_path = os.path.join(directory, filename.replace(".avi", ".mp4"))
            
            print(f"Converting {avi_path} to {mp4_path}...")
            
            # FFmpeg command for re-encoding AVI to MP4
            command = [
                "ffmpeg",
                "-i", avi_path,         # Input file
                "-c:v", "libx264",      # Use CPU encoding to avoid NVIDIA issues
                "-preset", "fast",      # Encoding speed
                "-crf", "23",           # Quality (lower is better, 23 is default)
                "-c:a", "aac",          # Audio codec
                "-b:a", "128k",         # Audio bitrate
                mp4_path                # Output file
            ]
            
            try:
                subprocess.run(command, check=True)
                print(f"Successfully converted {avi_path} to {mp4_path}")

                # Delete the original .avi file
                os.remove(avi_path)
                print(f"Deleted original file: {avi_path}")

            except subprocess.CalledProcessError as e:
                print(f"Error converting {avi_path}: {e}")

def face_logs(request):
    user_privilege = AccountRegistration.objects.filter(username=request.user).values()
    logs = FaceLogs.objects.all().order_by('-created_at')  # Latest first

    template = loader.get_template('live-feed/face_logs.html')
    context = {
        'user_role': user_privilege[0]['privilege'],
        'logs': logs,
    }
    return HttpResponse(template.render(context, request))

def log(id_number):
    """Log a face detection and return user info for display"""
    try:
        acc_info = AccountRegistration.objects.get(id_number=id_number)
        FaceLogs.objects.create(
            id_number=acc_info,
            first_name=acc_info.first_name,
            middle_name=acc_info.middle_name,
            last_name=acc_info.last_name,
        )
        return acc_info
    except ObjectDoesNotExist:
        print(f"No account found for id_number {id_number}")
        return None

# =======================================================
# Face frame queue and processing
face_frame_queue = Queue(maxsize=10)

def init_face_camera():
    """Initialize the face camera with DirectShow"""
    if face_cam_id in cameras and cameras[face_cam_id] is not None:
        return cameras[face_cam_id]
    else:
        try:
            # Prefer configured backend, with fallback
            for backend in (_BACKEND_MAP.get(PREFERRED_BACKEND, 0), _BACKEND_MAP.get('msmf', 0), _BACKEND_MAP.get('dshow', 0), 0):
                cap = cv2.VideoCapture(face_cam_id, backend)
                if cap.isOpened():
                    break
                cap.release()
            # If not opened, return None
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
                cap.set(cv2.CAP_PROP_FPS, FPS)
                return cap
        except Exception as e:
            print(f"Failed to initialize face camera: {e}")
    return None

# Only initialize the face camera eagerly if auto-start is enabled
face_cam = init_face_camera() if AUTO_START_CAMERAS else None

def frame_status_view(request):
    try:
        # Get the current capture step from the request
        current_step = request.GET.get('step', 'front')
        
        # Check if any face camera is initialized
        if not face_cameras or all(cam is None for cam in face_cameras.values()):
            return JsonResponse({'status': 'camera_not_ready', 'message': 'Please initialize camera first'})
        
        # Camera is initialized, check for frames
        timeout = 0.5  # Reduced timeout for better responsiveness
        start_time = time.time()
        
        # Try to get frame from the active face camera directly if queue is empty
        active_camera = None
        for cam_id, camera in face_cameras.items():
            if camera is not None:
                active_camera = camera
                break
        
        frame = None
        
        # First try to get from queue
        if not face_frame_queue.empty():
            frame = face_frame_queue.get()
        # If queue is empty but camera exists, read directly
        elif active_camera is not None:
            try:
                ret, direct_frame = active_camera.read()
                if ret and direct_frame is not None:
                    frame = direct_frame
            except Exception as cam_error:
                print(f"Direct camera read error: {cam_error}")
        
        if frame is not None:
            # Analyze frame for face quality and angle
            status_result = analyze_face_for_capture(frame, current_step)
            return JsonResponse(status_result)
        else:
            # Camera is ready but no frame available yet
            return JsonResponse({'status': 'camera_ready', 'message': 'Camera ready - waiting for frames'})
            
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def analyze_face_for_capture(frame, required_step='front'):
    """
    Analyze frame for face quality, angle, and capture readiness
    Returns status with next required capture step
    """
    try:
        # Use the step passed from frontend
        capture_sequence = ['front', 'left', 'right']
        
        # Resize for faster detection
        frame_small = cv2.resize(frame, (320, 240))
        original_height, original_width = frame.shape[:2]
        
        # Detect faces using cascade classifier
        gray = cv2.cvtColor(frame_small, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5, minSize=(30, 30))

        if len(faces) == 0:
            return {'status': 'no_face', 'message': 'Analyzing...'}  # Show "Analyzing..." when no face
        elif len(faces) > 1:
            return {'status': 'multiple_faces', 'message': 'Multiple faces detected'}
        
        # Single face detected - analyze quality and angle
        (x, y, w, h) = faces[0]
        
        # Scale face coordinates back to original frame size
        scale_x = original_width / 320
        scale_y = original_height / 240
        face_x = int(x * scale_x)
        face_y = int(y * scale_y)
        face_w = int(w * scale_x)
        face_h = int(h * scale_y)
        
        # Extract face region from original frame
        face_region = frame[face_y:face_y+face_h, face_x:face_x+face_w]
        
        if face_region.size == 0:
            return {'status': 'no_face', 'message': 'Invalid face region'}
        
        # Check image quality
        quality_result = check_face_quality(face_region)
        if not quality_result['is_good']:
            return {
                'status': 'poor_quality', 
                'message': quality_result['reason'],
                'next_capture': 'front'  # Default to front if quality is poor
            }
        
        # Determine face angle
        face_angle = determine_face_angle(face_region, (face_x, face_y, face_w, face_h))
        
        # Use the required step from the frontend
        next_capture = required_step
        
        # Check if current face angle matches what we need
        if face_angle == next_capture:
            return {
                'status': 'ready_to_capture',
                'message': f'Face positioned correctly for {next_capture} capture',
                'next_capture': next_capture,
                'face_angle': face_angle
            }
        else:
            return {
                'status': 'wrong_angle',
                'message': f'Please turn your face to show {next_capture} angle',
                'next_capture': next_capture,
                'current_angle': face_angle
            }
            
    except Exception as e:
        return {'status': 'error', 'message': f'Analysis error: {str(e)}'}


def check_face_quality(face_region):
    """
    Check if face image quality is good enough for capture
    Returns dict with is_good boolean and reason
    """
    try:
        # Convert to grayscale for analysis
        gray_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
        
        # Check for blur using Laplacian variance
        laplacian_var = cv2.Laplacian(gray_face, cv2.CV_64F).var()
        blur_threshold = 100  # Lower values indicate more blur
        
        if laplacian_var < blur_threshold:
            return {'is_good': False, 'reason': 'Image too blurry - please hold still'}
        
        # Check brightness
        mean_brightness = gray_face.mean()
        if mean_brightness < 50:
            return {'is_good': False, 'reason': 'Too dark - please improve lighting'}
        elif mean_brightness > 200:
            return {'is_good': False, 'reason': 'Too bright - please reduce lighting'}
        
        # Check if face is large enough
        min_face_size = 80  # Minimum width/height
        if face_region.shape[0] < min_face_size or face_region.shape[1] < min_face_size:
            return {'is_good': False, 'reason': 'Move closer to camera'}
        
        return {'is_good': True, 'reason': 'Good quality'}
        
    except Exception as e:
        return {'is_good': False, 'reason': f'Quality check error: {str(e)}'}


def determine_face_angle(face_region, face_coords):
    """
    Determine if face is showing front, left, or right angle
    Enhanced implementation using multiple facial features
    """
    try:
        gray_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
        
        # Use multiple cascade classifiers for better detection
        eye_cascade_path = cv2.data.haarcascades + 'haarcascade_eye.xml'
        nose_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'  # Repurpose for nose area
        
        eye_cascade = cv2.CascadeClassifier(eye_cascade_path)
        
        # Detect eyes
        eyes = eye_cascade.detectMultiScale(gray_face, 1.1, 3, minSize=(8, 8))
        
        face_width = face_region.shape[1]
        face_height = face_region.shape[0]
        face_center_x = face_width // 2
        
        if len(eyes) >= 2:
            # Sort eyes by x-coordinate (left to right in image)
            eyes = sorted(eyes, key=lambda x: x[0])
            
            # Get eye centers
            left_eye_center = (eyes[0][0] + eyes[0][2] // 2, eyes[0][1] + eyes[0][3] // 2)
            right_eye_center = (eyes[1][0] + eyes[1][2] // 2, eyes[1][1] + eyes[1][3] // 2)
            
            # Calculate eye positions relative to face center
            left_eye_offset = left_eye_center[0] - face_center_x
            right_eye_offset = right_eye_center[0] - face_center_x
            
            # Calculate asymmetry
            eye_asymmetry = abs(abs(left_eye_offset) - abs(right_eye_offset))
            symmetry_threshold = face_width * 0.25  # 25% of face width - LESS STRICT for easier capture
            
            # Check if eyes are roughly symmetrical (front view)
            if eye_asymmetry < symmetry_threshold:
                return 'front'
            
            # Determine profile direction based on which eye is more visible/central
            if abs(left_eye_offset) < abs(right_eye_offset):
                # Left eye is closer to center, showing right profile
                return 'right'
            else:
                # Right eye is closer to center, showing left profile  
                return 'left'
                
        elif len(eyes) == 1:
            # Only one eye visible - likely a profile view
            eye_x = eyes[0][0] + eyes[0][2] // 2
            
            # Determine which side based on eye position
            if eye_x < face_center_x:
                return 'left'  # Eye on left side of face region
            else:
                return 'right'  # Eye on right side of face region
        else:
            # No eyes detected - use face position analysis as fallback
            # This is a basic heuristic
            face_x, face_y, face_w, face_h = face_coords
            
            # Check if face is roughly centered (front view more likely)
            # This is a simplified fallback
            return 'front'
            
    except Exception as e:
        return 'front'  # Default to front on error


def determine_next_capture_step():
    """
    Determine which capture step is needed next
    This integrates with the frontend's capture sequence logic
    """
    # For now, we'll return the first step as the frontend manages the full sequence
    # The frontend will handle disabling the capture when face isn't ready
    # In a full implementation, you could store progress in session or database
    return 'front'  # Frontend handles the actual sequence progression

# Capture loop with frame skipping
def capture_face_frames():
    frame_count = 0
    consecutive_failures = 0
    
    while running:
        try:
            if face_cam is None:
                time.sleep(1)
                continue
                
            ret, frame = face_cam.read()
            frame_count += 1
            
            if not ret:
                consecutive_failures += 1
                if consecutive_failures > 10:
                    print("Reinitializing face camera...")
                    if face_cam.isOpened():
                        face_cam.release()
                    time.sleep(1)
                    globals()['face_cam'] = init_face_camera()
                    consecutive_failures = 0
                continue
                
            consecutive_failures = 0
            
            # Only process every few frames to improve performance
            if frame_count % FRAME_SKIP == 0 and not face_frame_queue.full():
                # Make array contiguous for better processing
                frame = np.ascontiguousarray(frame)
                face_frame_queue.put(frame)
                
        except Exception as e:
            print(f"Error in face capture: {e}")
            time.sleep(0.5)
        
        # Control frame rate
        time.sleep(max(1/FPS - 0.01, 0.01))

# Start the capture thread only when auto-start is enabled
if AUTO_START_CAMERAS:
    Thread(target=capture_face_frames, daemon=True).start()
else:
    print("Face camera capture thread not started (CAMERA_AUTO_START=0)")

# Add recording management thread
def recording_management():
    """Periodically manages recordings - ensures they're not too large,
    and converts completed recordings to MP4 for archive viewing"""
    global recording
    last_reset_time = time.time()
    
    while running:
        current_time = time.time()
        elapsed_hours = (current_time - last_reset_time) / 3600
        
        # Every 1 hour, reset the recordings to prevent huge files
        if elapsed_hours >= 1:
            print("Performing scheduled recording rotation")
            # Stop current recording
            for cam_id in video_writers:
                if video_writers[cam_id] and video_writers[cam_id].isOpened():
                    video_writers[cam_id].release()
            
            # Convert any AVI files
            recordings_dir = os.path.join(settings.BASE_DIR, 'recordings')
            reencode_avi_to_mp4(recordings_dir)
            
            # Start new recording if we were recording
            if recording:
                initialize_video_writers()
            
            last_reset_time = current_time
        
        time.sleep(60)  # Check every minute

# Start the recording management thread
Thread(target=recording_management, daemon=True).start()

def recording_status(request):
    """Returns the current recording status and forces recording to start if it's not already running"""
    global recording, video_writers
    
    status = {
        'is_recording': recording,
        'active_writers': len(video_writers),
        'camera_count': len(cameras),
        'recording_paths': []
    }
    
    # Check if recording directories exist
    recordings_dir = os.path.join(settings.BASE_DIR, 'recordings')
    if os.path.exists(recordings_dir):
        status['recordings_dir_exists'] = True
        # List recent recordings
        files = [f for f in os.listdir(recordings_dir) if f.endswith('.avi') or f.endswith('.mp4')]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(recordings_dir, x)), reverse=True)
        status['recent_files'] = files[:5]  # Get 5 most recent files
    else:
        status['recordings_dir_exists'] = False
    
    # Force recording to start if it's not
    if not recording:
        recording = True
        initialize_video_writers()
        status['recording_started'] = True
    
    return JsonResponse(status)

def face_enrollment_feed(request):
    """Special video feed for face enrollment"""
    # Use camera 0 by default for face enrollment
    enrollment_camera_id = 0
    if enrollment_camera_id not in cameras:
        # Fall back to first available camera
        enrollment_camera_id = list(cameras.keys())[0] if cameras else 0

    # Make sure we have the camera initialized
    if cameras[enrollment_camera_id] is None:
        # Attempt to reinitialize camera
        try:
            cap = cv2.VideoCapture(enrollment_camera_id, cv2.CAP_DSHOW)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
                cap.set(cv2.CAP_PROP_FPS, FPS)
                cameras[enrollment_camera_id] = cap
                print(f"Reinitialized camera {enrollment_camera_id} for face enrollment")
        except Exception as e:
            print(f"Failed to initialize face enrollment camera: {e}")
    
    # Route to the video feed for this camera
    return StreamingHttpResponse(generate(enrollment_camera_id), 
                               content_type='multipart/x-mixed-replace; boundary=frame')

# Debug endpoint that dumps the current state of face embeddings 
def debug_embeddings(request):
    """Debug endpoint to check face embeddings"""
    # Only allow staff access
    if not request.user.is_staff:
        return HttpResponse("Unauthorized", status=403)
        
    try:
        # Reload embeddings
        matcher.load_embeddings()
        
        # Get embedding stats
        stats = {
            'embedding_count': len(matcher.embeddings),
            'embedding_ids': list(matcher.embeddings.keys()),
            'has_cuda': torch.cuda.is_available(),
            'gpu_status': gpu_status
        }
        
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({'error': str(e)})

# Start a separate thread for each camera
for cam_id in cameras:
    Thread(target=capture_frames, args=(cam_id,), daemon=True).start()

def find_ffmpeg():
    """Try to find ffmpeg in system PATH or common locations."""
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path
    # Try common locations
    possible_paths = [
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "C:\\ffmpeg\\bin\\ffmpeg.exe",
        "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
        "C:\\Program Files (x86)\\ffmpeg\\bin\\ffmpeg.exe",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def convert_video_for_preview(request):
    """Converts an AVI file to MP4 for preview playback"""
    try:
        if request.method == 'GET':
            filename = request.GET.get('filename')
            if not filename:
                return JsonResponse({'success': False, 'error': 'No filename provided'})
                
            # Security check - prevent directory traversal
            if '..' in filename or '/' in filename:
                return JsonResponse({'success': False, 'error': 'Invalid filename'})
                
            recordings_dir = os.path.join(settings.BASE_DIR, 'recordings')
            file_path = os.path.join(recordings_dir, filename)
            
            # If file doesn't exist
            if not os.path.exists(file_path):
                return JsonResponse({'success': False, 'error': f'File not found: {filename}'})
                
            # If already MP4, just return the path
            if filename.endswith('.mp4'):
                return JsonResponse({'success': True, 'mp4_file': filename})
                
            # For AVI files, convert to MP4
            if filename.endswith('.avi'):
                mp4_filename = filename.replace('.avi', '.mp4')
                mp4_path = os.path.join(recordings_dir, mp4_filename)
                
                # Only convert if MP4 doesn't exist yet
                if not os.path.exists(mp4_path):
                    ffmpeg_bin = find_ffmpeg()
                    if not ffmpeg_bin:
                        return JsonResponse({'success': False, 'error': 'FFmpeg not found on server. Please install FFmpeg and ensure it is in your PATH.'})
                    try:
                        # FFmpeg command for re-encoding AVI to MP4
                        command = [
                            ffmpeg_bin,
                            "-i", file_path,         # Input file
                            "-c:v", "libx264",       # Video codec
                            "-preset", "ultrafast",  # Faster conversion for preview
                            "-crf", "28",            # Lower quality is OK for preview
                            "-c:a", "aac",           # Audio codec
                            "-b:a", "128k",          # Audio bitrate
                            "-y",                    # Overwrite output file
                            mp4_path                 # Output file
                        ]
                        result = subprocess.run(command, check=True, capture_output=True)
                        print(f"Successfully converted {filename} to {mp4_filename}")
                    except subprocess.CalledProcessError as e:
                        error_message = e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e)
                        print(f"FFmpeg error: {error_message}")
                        return JsonResponse({'success': False, 'error': f'FFmpeg error: {error_message}'})
                    except Exception as e:
                        print(f"Conversion error: {str(e)}")
                        return JsonResponse({'success': False, 'error': f'Conversion error: {str(e)}'})
                        
                return JsonResponse({'success': True, 'mp4_file': mp4_filename})
                
        return JsonResponse({'success': False, 'error': 'Invalid request'})
    except Exception as e:
        import traceback
        print(f"Unexpected error in convert_video_for_preview: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'})

def get_available_cameras(request):
    """API endpoint to get available cameras for dropdown selection"""
    try:
        cameras_info = get_available_cameras_info()
        return JsonResponse({'success': True, 'cameras': cameras_info})
    except Exception as e:
        import traceback
        print(f"Error getting available cameras: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': f'Error detecting cameras: {str(e)}'})