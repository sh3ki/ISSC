"""
Improved Live Feed Video Handling
This module provides enhanced camera initialization and management for the live feed page.
Addresses flickering issu    def _fast_initialize(self):
        \"\"\"Fast initialization - get page loaded quickly with stable frames\"\"\"
        # Always initialize exactly 4 cameras [0, 1, 2, 3]
        expected_camera_ids = [0, 1, 2, 3]
        
        self.cameras =        return frame
    
    def _generate_connecting_frame(self, camera_id):
        \"\"\"Generate a stable 'Connecting...' frame to prevent flickering\"\"\"
        frame = np.zeros((self.FRAME_HEIGHT, self.FRAME_WIDTH, 3), dtype=np.uint8)
        
        # Create a blue-tinted background
        for y in range(self.FRAME_HEIGHT):
            intensity = 25 + int(15 * (y / self.FRAME_HEIGHT))
            frame[y, :] = [intensity//2, intensity//2, intensity]
        
        # Add camera info
        if camera_id == 0:
            cam_text = \"CAMERA 0 - BUILT-IN\"
        elif camera_id == 1:
            cam_text = \"CAMERA 1 - EXTERNAL\"
        else:
            cam_text = f\"CAMERA {camera_id} - ADDITIONAL\"
            
        cv2.putText(frame, cam_text, (50, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 200), 2)
        
        # Add status message
        cv2.putText(frame, \"CONNECTING...\", (50, self.FRAME_HEIGHT//2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (100, 150, 255), 2)
        
        # Add a progress indicator (static for stability)
        center_x, center_y = self.FRAME_WIDTH//2, self.FRAME_HEIGHT//2 + 50
        cv2.rectangle(frame, (center_x-100, center_y-10), (center_x+100, center_y+10), (100, 150, 255), 2)
        cv2.rectangle(frame, (center_x-98, center_y-8), (center_x-20, center_y+8), (100, 150, 255), -1)
        
        return frame
    
    def _generate_error_frame(self, camera_id, error_message=\"Error\"):
        self.frame_queues = {}
        self.display_states = {}
        self.capture_threads = {}
        
        # Initialize all 4 cameras immediately with stable \"connecting\" frames
        for camera_id in expected_camera_ids:
            self.cameras[camera_id] = None  # Will be replaced by real cameras
            self.frame_queues[camera_id] = Queue(maxsize=3)
            
            # Initialize display state to prevent flickering
            self.display_states[camera_id] = {
                \"face_count\": 0,
                \"previous_face_count\": 0,
                \"last_update\": time.time(),
                \"face_locations\": [],
                \"face_matches\": [],
                \"stable_since\": time.time(),
                \"update_needed\": False,
                \"error_count\": 0,
                \"last_successful_frame\": time.time(),
                \"initializing\": False,  # Set to False to prevent flickering
                \"status\": \"connecting\"
            }
            
            # Pre-fill with stable \"connecting\" frame to prevent flickering
            stable_frame = self._generate_connecting_frame(camera_id)
            self.frame_queues[camera_id].put(stable_frame)es stable camera operation.
"""

import cv2
import time
import numpy as np
from threading import Thread, Lock
from queue import Queue
import os
from datetime import datetime
import torch

from django.http import HttpResponse, StreamingHttpResponse
from django.template import loader
from django.contrib.auth.decorators import login_required

from ..models import AccountRegistration
from django.conf import settings
from ..computer_vision.face_matching import FaceMatcher
from ..computer_vision.face_enrollment import FaceEnrollment
from ..utils.philsms import send_sms_async

# Enhanced camera management
class EnhancedCameraManager:
    def __init__(self):
        self.cameras = {}
        self.frame_queues = {}
        self.display_states = {}
        self.capture_threads = {}
        self.running = False
        self.lock = Lock()
        
        # Video settings
        self.FRAME_WIDTH = 560
        self.FRAME_HEIGHT = 420
        self.FPS = 30  # ⚡ LIGHTNING FAST - Increased from 20
        self.FRAME_SKIP = 8  # ⚡ LIGHTNING FAST - Process every 8th frame (was 4)
        
        # Initialize face detection components
        self.face_detector = FaceEnrollment(device='cuda')
        # Initialize with GPU support and relaxed threshold for speed
        self.matcher = FaceMatcher(use_gpu=True, threshold=0.65)  # ⚡ Relaxed for speed
        self.matcher.load_embeddings()
        
        # Error handling
        self.last_error_time = 0
        self.error_cooldown = 5

        # SMS notification rate limiting
        # Global last-sent epoch timestamp (enforce one SMS every N seconds)
        self._last_sms_sent_global = 0
        # Cooldown in seconds (read from settings if available)
        try:
            self._sms_cooldown = int(getattr(settings, 'PHILSMS_COOLDOWN_SECONDS', 15 * 60))
        except Exception:
            self._sms_cooldown = 15 * 60
        
        # Initialize Haar cascade as fallback
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
    def detect_working_cameras(self):
        """Detect and test cameras with improved reliability, excluding virtual cameras"""
        working_cameras = {}
        print("Enhanced camera detection starting (excluding NVIDIA/OBS virtual cameras)...")
        
        # Test up to 8 camera indices to find real cameras
        for camera_id in range(8):
            try:
                # Try different backends
                backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, 0]
                
                for backend in backends:
                    cap = cv2.VideoCapture(camera_id, backend)
                    
                    if not cap.isOpened():
                        cap.release()
                        continue
                    
                    # Check if this is a virtual camera (NVIDIA/OBS) by testing device name
                    try:
                        # Get camera name/description if possible
                        import platform
                        if platform.system() == "Windows":
                            # On Windows, we can try to get device info
                            # Skip if it's a known virtual camera
                            pass  # We'll rely on stability testing to filter virtual cameras
                    except:
                        pass
                    
                    # Configure camera for stability and anti-flickering
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.FRAME_WIDTH)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.FRAME_HEIGHT)
                    cap.set(cv2.CAP_PROP_FPS, self.FPS)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffer to reduce lag
                    
                    # Anti-flickering settings
                    try:
                        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Manual exposure mode
                        cap.set(cv2.CAP_PROP_EXPOSURE, -6)  # Fixed exposure value
                    except:
                        pass  # Some cameras don't support these settings
                    
                    # Test camera stability
                    test_passed = True
                    consecutive_success = 0
                    
                    for test_frame in range(5):
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.shape[0] > 0 and frame.shape[1] > 0:
                            consecutive_success += 1
                        time.sleep(0.1)
                    
                    if consecutive_success >= 4:  # At least 4/5 successful reads
                        print(f"Camera {camera_id} initialized successfully (backend: {backend})")
                        working_cameras[camera_id] = cap
                        break
                    else:
                        cap.release()
                        
            except Exception as e:
                print(f"Error testing camera {camera_id}: {e}")
                
        # Filter out virtual cameras and organize real cameras
        real_cameras_found = {k: v for k, v in working_cameras.items() if v is not None}
        
        # Reorganize cameras: assign first real camera to index 0 (Acer), second to index 1 (external webcam)
        final_cameras = {}
        real_camera_list = list(real_cameras_found.items())
        
        # Always provide exactly 4 camera slots
        for slot_id in range(4):
            if slot_id < len(real_camera_list):
                # Assign real camera to this slot
                original_id, cap = real_camera_list[slot_id]
                final_cameras[slot_id] = cap
                if slot_id == 0:
                    print(f"Camera {slot_id}: Acer built-in camera (originally camera {original_id})")
                elif slot_id == 1:
                    print(f"Camera {slot_id}: External webcam (originally camera {original_id})")
                else:
                    print(f"Camera {slot_id}: Additional camera (originally camera {original_id})")
            else:
                # No real camera for this slot
                final_cameras[slot_id] = None
                print(f"Camera {slot_id}: No Input (no camera detected)")
        
        print(f"Camera detection complete. Active cameras: {[k for k, v in final_cameras.items() if v is not None]}")
        return final_cameras
    
    def initialize_for_live_feed(self, fast_init=True):
        """Initialize cameras specifically for live feed with FAST startup"""
        with self.lock:
            if self.running:
                return  # Already running, skip reinitialization
            
            print("Fast initializing enhanced camera system...")
            
            if fast_init:
                # FAST INITIALIZATION - Load page immediately, cameras in background
                self._fast_initialize()
            else:
                # STANDARD INITIALIZATION - Wait for all cameras
                self._standard_initialize()
    
    def _fast_initialize(self):
        """Fast initialization - get page loaded quickly"""
        # Pre-populate with common camera IDs for instant display
        common_camera_ids = [0, 1, 2]  # Most common camera indices
        
        self.cameras = {}
        self.frame_queues = {}
        self.display_states = {}
        self.capture_threads = {}
        
        # Initialize placeholders immediately
        for camera_id in common_camera_ids:
            self.cameras[camera_id] = None  # Will be initialized in background
            self.frame_queues[camera_id] = Queue(maxsize=2)  # Smaller buffer
            self.display_states[camera_id] = {
                "face_count": 0,
                "previous_face_count": 0,
                "last_update": time.time(),
                "face_locations": [],
                "face_matches": [],
                "stable_since": time.time(),
                "update_needed": False,
                "error_count": 0,
                "last_successful_frame": time.time(),
                "initializing": True
            }
        
        self.running = True
        
        # Start background initialization
        init_thread = Thread(target=self._background_camera_init, daemon=True)
        init_thread.start()
        
        print("Fast initialization complete - cameras loading in background")
    
    def _background_camera_init(self):
        """Initialize cameras in background for seamless experience"""
        try:
            print("Background camera initialization starting...")
            
            # Detect actual working cameras
            working_cameras = self.detect_working_cameras()
            
            # Update with real cameras
            with self.lock:
                # Remove placeholder cameras that don't exist
                cameras_to_remove = []
                for camera_id in list(self.cameras.keys()):
                    if camera_id not in working_cameras:
                        cameras_to_remove.append(camera_id)
                
                for camera_id in cameras_to_remove:
                    if camera_id in self.cameras:
                        del self.cameras[camera_id]
                    if camera_id in self.frame_queues:
                        del self.frame_queues[camera_id]
                    if camera_id in self.display_states:
                        del self.display_states[camera_id]
                
                # Add real cameras
                for camera_id, cap in working_cameras.items():
                    self.cameras[camera_id] = cap
                    if camera_id not in self.frame_queues:
                        self.frame_queues[camera_id] = Queue(maxsize=2)
                    if camera_id not in self.display_states:
                        self.display_states[camera_id] = {
                            "face_count": 0,
                            "previous_face_count": 0,
                            "last_update": time.time(),
                            "face_locations": [],
                            "face_matches": [],
                            "stable_since": time.time(),
                            "update_needed": False,
                            "error_count": 0,
                            "last_successful_frame": time.time(),
                            "initializing": False
                        }
            
            # Start capture threads for real cameras
            for camera_id in working_cameras:
                if camera_id not in self.capture_threads:
                    thread = Thread(target=self._stable_capture_loop, args=(camera_id,), daemon=True)
                    thread.start()
                    self.capture_threads[camera_id] = thread
            
            print(f"Background camera initialization complete: {list(working_cameras.keys())}")
            
        except Exception as e:
            print(f"Error in background camera initialization: {e}")
    
    def _standard_initialize(self):
        """Standard initialization - wait for all cameras (slower but thorough)"""
        # Detect working cameras
        self.cameras = self.detect_working_cameras()
        
        # Initialize frame queues and display states
        self.frame_queues = {}
        self.display_states = {}
        
        for camera_id in self.cameras:
            self.frame_queues[camera_id] = Queue(maxsize=2)  # Smaller buffer
            self.display_states[camera_id] = {
                "face_count": 0,
                "previous_face_count": 0,
                "last_update": time.time(),
                "face_locations": [],
                "face_matches": [],
                "stable_since": time.time(),
                "update_needed": False,
                "error_count": 0,
                "last_successful_frame": time.time(),
                "initializing": False
            }
        
        # Start capture threads
        self.running = True
        self.capture_threads = {}
        
        for camera_id in self.cameras:
            thread = Thread(target=self._stable_capture_loop, args=(camera_id,), daemon=True)
            thread.start()
            self.capture_threads[camera_id] = thread
        
        print(f"Enhanced camera system initialized with {len(self.cameras)} cameras")
    
    def _stable_capture_loop(self, camera_id):
        """Enhanced capture loop with better error handling and stability"""
        cap = self.cameras[camera_id]
        frame_count = 0
        consecutive_failures = 0
        max_failures = 15
        
        # Pre-generate a stable "no signal" frame to avoid repeated generation
        no_signal_frame = self._generate_stable_no_signal_frame(camera_id)
        
        while self.running:
            try:
                current_time = time.time()
                
                if cap is None:
                    # Dummy camera - provide stable placeholder
                    if not self.frame_queues[camera_id].full():
                        self.frame_queues[camera_id].put(no_signal_frame.copy())
                    time.sleep(1/self.FPS)
                    continue
                
                success, frame = cap.read()
                
                if not success or frame is None:
                    consecutive_failures += 1
                    
                    # Use stable no-signal frame
                    frame = no_signal_frame.copy()
                    
                    # Try to recover the camera if too many failures
                    if consecutive_failures > max_failures:
                        print(f"Attempting to recover camera {camera_id}")
                        cap.release()
                        time.sleep(1)
                        
                        # Try to reinitialize
                        new_cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
                        if new_cap.isOpened():
                            new_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.FRAME_WIDTH)
                            new_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.FRAME_HEIGHT)
                            new_cap.set(cv2.CAP_PROP_FPS, self.FPS)
                            new_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            
                            self.cameras[camera_id] = new_cap
                            cap = new_cap
                            consecutive_failures = 0
                            print(f"Camera {camera_id} recovered successfully")
                        else:
                            print(f"Failed to recover camera {camera_id}, switching to dummy mode")
                            self.cameras[camera_id] = None
                            cap = None
                else:
                    consecutive_failures = 0
                    self.display_states[camera_id]["last_successful_frame"] = current_time
                    
                    # Process frame for face detection (every Nth frame)
                    frame_count += 1
                    if frame_count % self.FRAME_SKIP == 0:
                        frame = self._process_frame_with_face_detection(frame, camera_id)
                    else:
                        # For non-processed frames, just add overlay
                        frame = self._add_stable_overlay(frame, camera_id)
                
                # Manage frame queue size to prevent buildup
                if self.frame_queues[camera_id].full():
                    try:
                        self.frame_queues[camera_id].get_nowait()  # Remove oldest frame
                    except:
                        pass
                
                self.frame_queues[camera_id].put(frame)
                
                # Proper timing to maintain FPS
                time.sleep(max(1/self.FPS - 0.005, 0.01))
                
            except Exception as e:
                consecutive_failures += 1
                current_time = time.time()

                # Rate-limited error logging
                if current_time - self.last_error_time > self.error_cooldown:
                    print(f"Camera {camera_id} error: {e}")
                    self.last_error_time = current_time

                # Use stable no-signal frame on error
                try:
                    if not self.frame_queues[camera_id].full():
                        self.frame_queues[camera_id].put(no_signal_frame.copy())
                except Exception:
                    pass

                time.sleep(0.1)  # Brief pause on error
    
    def _generate_stable_no_signal_frame(self, camera_id):
        """Generate a stable, non-flickering 'No Signal' frame"""
        frame = np.zeros((self.FRAME_HEIGHT, self.FRAME_WIDTH, 3), dtype=np.uint8)
        
        # Create a subtle gradient background
        for y in range(self.FRAME_HEIGHT):
            intensity = 20 + int(20 * (y / self.FRAME_HEIGHT))
            frame[y, :] = [intensity, intensity, intensity]
        
        # Add camera info
        cv2.putText(frame, f"CAMERA {camera_id}", (50, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (200, 200, 200), 2)
        
        # Add status message
        cv2.putText(frame, "INITIALIZING...", (50, self.FRAME_HEIGHT//2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 150, 255), 2)
        
        # Add a simple animated element (static for stability)
        center_x, center_y = self.FRAME_WIDTH//2, self.FRAME_HEIGHT//2 + 50
        cv2.circle(frame, (center_x, center_y), 30, (100, 150, 255), 2)
        cv2.circle(frame, (center_x, center_y), 20, (100, 150, 255), 1)
        cv2.circle(frame, (center_x, center_y), 10, (100, 150, 255), 1)
        
        return frame
    
    def _generate_error_frame(self, camera_id, error_message="Error"):
        """Generate an error frame for display"""
        frame = np.zeros((self.FRAME_HEIGHT, self.FRAME_WIDTH, 3), dtype=np.uint8)
        
        # Create a red-tinted background
        for y in range(self.FRAME_HEIGHT):
            intensity = 15 + int(10 * (y / self.FRAME_HEIGHT))
            frame[y, :] = [intensity, intensity//2, intensity//2]
        
        # Add camera info
        cv2.putText(frame, f"CAMERA {camera_id}", (50, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (200, 200, 200), 2)
        
        # Add error message
        cv2.putText(frame, "ERROR", (50, self.FRAME_HEIGHT//2 - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (100, 100, 255), 2)
        
        # Add specific error (truncated if too long)
        error_text = error_message[:30] + "..." if len(error_message) > 30 else error_message
        cv2.putText(frame, error_text, (50, self.FRAME_HEIGHT//2 + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 255), 2)
        
        return frame
    
    def _add_stable_overlay(self, frame, camera_id):
        """Add minimal overlay - only face count at top-left"""
        display_frame = frame.copy()
        
        # Only show face count with stable display
        face_count = self.display_states[camera_id].get('face_count', 0)
        
        # Simple text overlay with shadow for visibility
        text = f"Faces: {face_count}"
        
        # Add text shadow (black background)
        cv2.putText(display_frame, text, (12, 32), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 3)
        
        # Add main text (colored based on face count)
        color = (0, 255, 0) if face_count > 0 else (200, 200, 200)
        cv2.putText(display_frame, text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        return display_frame
    
    def _process_frame_with_face_detection(self, frame, camera_id):
        """Process frame with enhanced face detection and recognition"""
        try:
            display_frame = frame.copy()
            
            # Resize for faster processing
            small_frame = cv2.resize(frame, (320, 240))
            small_frame = np.ascontiguousarray(small_frame)
            
            face_crops = []
            face_locations = []
            
            # ⚡ LIGHTNING FAST - Use ONLY Haar Cascade (no MTCNN fallback)
            try:
                gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                opencv_faces = self.face_cascade.detectMultiScale(gray, 1.3, 5, minSize=(30, 30))
                
                for (x, y, w, h) in opencv_faces:
                    # ⚡ SKIP if face too small (speeds up processing)
                    if w >= 30 and h >= 30:
                        face_crops.append(small_frame[y:y+h, x:x+w])
                        face_locations.append(np.array([y, y+h, x, x+w]))
                    
            except Exception:
                pass
            
            # Update face count
            face_count = len(face_crops)
            self.display_states[camera_id]['face_count'] = face_count
            
            # ⚡ SKIP processing if no faces detected (saves resources + no empty images)
            if face_count == 0:
                display_frame = self._add_stable_overlay(display_frame, camera_id)
                return display_frame
            
            # Process face recognition if faces detected
            if face_crops and face_locations:
                scaled_locations, match_results = self._process_face_recognition(
                    frame, face_crops, face_locations, small_frame.shape, frame.shape, camera_id)
                
                # Update display state
                self.display_states[camera_id]['face_locations'] = scaled_locations
                self.display_states[camera_id]['face_matches'] = match_results
                self.display_states[camera_id]['last_update'] = time.time()
            
            # Add overlay and face boxes
            display_frame = self._add_stable_overlay(display_frame, camera_id)
            display_frame = self._draw_stable_face_boxes(display_frame, camera_id)
            
            return display_frame
            
        except Exception as e:
            current_time = time.time()
            if current_time - self.last_error_time > self.error_cooldown:
                print(f"Face processing error for camera {camera_id}: {e}")
                self.last_error_time = current_time
            return self._add_stable_overlay(frame, camera_id)
    
    def _process_face_recognition(self, frame, face_crops, face_locations, small_shape, full_shape, camera_id):
        """Process face recognition with error handling"""
        scaled_locations = []
        match_results = []
        
        # Calculate scaling factors
        h_scale = full_shape[0] / small_shape[0]
        w_scale = full_shape[1] / small_shape[1]
        
        for i, (face_crop, face_loc) in enumerate(zip(face_crops, face_locations)):
            try:
                # Scale coordinates to full frame
                if hasattr(face_loc, 'flatten'):
                    face_loc = face_loc.flatten()
                
                y1 = max(0, min(int(face_loc[0] * h_scale), full_shape[0]-1))
                y2 = max(0, min(int(face_loc[1] * h_scale), full_shape[0]-1))
                x1 = max(0, min(int(face_loc[2] * w_scale), full_shape[1]-1))
                x2 = max(0, min(int(face_loc[3] * w_scale), full_shape[1]-1))
                
                if x2 <= x1 or y2 <= y1:
                    continue
                
                scaled_locations.append((x1, y1, x2, y2))
                
                # Extract face for recognition
                face_img = frame[y1:y2, x1:x2]
                
                if face_img.shape[0] > 20 and face_img.shape[1] > 20:
                    try:
                        # Get embedding and match
                        embedding = self.face_detector.extract_embeddings(np.ascontiguousarray(face_img))
                        
                        if embedding is not None:
                            # ⚡ LIGHTNING FAST MATCHING - Relaxed threshold for speed
                            match_id, confidence = self.matcher.match(embedding, threshold=0.65)
                            
                            print(f"🔍 Face matching - ID: {match_id}, Confidence: {confidence:.2f}")
                            
                            # ✅ Check if this is a VALID match from enrolled users
                            is_authorized = False
                            if match_id and confidence >= 0.65:  # 0.65 = good enough (relaxed for speed)
                                # Verify the match_id exists in our embeddings database
                                try:
                                    if hasattr(self.matcher, 'embeddings') and self.matcher.embeddings:
                                        is_enrolled = match_id in self.matcher.embeddings
                                        if is_enrolled:
                                            is_authorized = True
                                            print(f"✅ AUTHORIZED - ID: {match_id} (Confidence: {confidence:.2f})")
                                        else:
                                            print(f"❌ ID {match_id} not in enrolled database")
                                except Exception as e:
                                    print(f"⚠️ Error checking enrollment: {e}")
                                    is_authorized = False
                            
                            if is_authorized and match_id:
                                # 🟢 GREEN BOX - Authorized/Matched face
                                try:
                                    from .utils import log
                                    user_info = log(match_id)
                                    print(f"🟢 GREEN BOX - {user_info.first_name if user_info else match_id}")
                                    match_results.append({
                                        'match_id': match_id,
                                        'confidence': confidence,
                                        'user_info': user_info,
                                        'is_authorized': True,
                                        'match_type': 'AUTHORIZED'
                                    })
                                except Exception as e:
                                    print(f"⚠️ Error getting user info: {e}")
                                    match_results.append({
                                        'match_id': match_id,
                                        'confidence': confidence,
                                        'user_info': None,
                                        'is_authorized': True,
                                        'match_type': 'AUTHORIZED'
                                    })
                            else:
                                # 🔴 RED BOX - Unauthorized/Unknown face
                                print(f"🔴 RED BOX - UNAUTHORIZED (Confidence: {confidence:.2f if confidence else 0.0})")
                                try:
                                    self._notify_unauthorized(camera_id)
                                except Exception as _e:
                                    print(f"Error notifying unauthorized: {_e}")
                                match_results.append({
                                    'match_id': None,
                                    'confidence': confidence if confidence else 0.0,
                                    'user_info': None,
                                    'is_authorized': False,
                                    'match_type': 'UNAUTHORIZED'
                                })
                        else:
                            print("DEBUG: No embedding extracted - UNAUTHORIZED")
                            try:
                                self._notify_unauthorized(camera_id)
                            except Exception as _e:
                                print(f"Error notifying unauthorized: {_e}")
                            match_results.append({
                                'match_id': None,
                                'confidence': 0.0,
                                'user_info': None,
                                'is_authorized': False,
                                'match_type': 'UNAUTHORIZED'
                            })
                            
                    except Exception as e:
                        print(f"DEBUG: Exception in face matching: {e} - UNAUTHORIZED")
                        try:
                            self._notify_unauthorized(camera_id)
                        except Exception as _e:
                            print(f"Error notifying unauthorized: {_e}")
                        match_results.append({
                            'match_id': None,
                            'confidence': 0.0,
                            'user_info': None,
                            'is_authorized': False,
                            'match_type': 'UNAUTHORIZED'
                        })
                else:
                    print("DEBUG: Face too small - UNAUTHORIZED")
                    try:
                        self._notify_unauthorized(camera_id)
                    except Exception as _e:
                        print(f"Error notifying unauthorized: {_e}")
                    match_results.append({
                        'match_id': None,
                        'confidence': 0.0,
                        'user_info': None,
                        'is_authorized': False,
                        'match_type': 'UNAUTHORIZED'
                    })
                    
            except Exception:
                continue
                
        return scaled_locations, match_results
    
    def _draw_stable_face_boxes(self, frame, camera_id):
        """✅ FULLY FUNCTIONAL - Draw GREEN boxes for matches, RED boxes for unauthorized faces"""
        if camera_id not in self.display_states:
            return frame
        
        display_frame = frame.copy()
        face_locations = self.display_states[camera_id].get('face_locations', [])
        face_matches = self.display_states[camera_id].get('face_matches', [])
        
        # Apply temporal smoothing to reduce flickering
        current_time = time.time()
        if not hasattr(self, '_stable_boxes'):
            self._stable_boxes = {}
        if camera_id not in self._stable_boxes:
            self._stable_boxes[camera_id] = []
        
        # Smooth face box positions
        smoothed_locations = self._smooth_face_boxes(face_locations, camera_id)
        
        for i, (x1, y1, x2, y2) in enumerate(smoothed_locations):
            match_info = face_matches[i] if i < len(face_matches) else None
            
            # ✅ DETERMINE IF AUTHORIZED (GREEN) OR UNAUTHORIZED (RED)
            is_authorized = False
            if match_info:
                is_authorized = (match_info.get('is_authorized', False) == True and 
                               match_info.get('match_type') == 'AUTHORIZED' and
                               match_info.get('match_id') is not None)
            
            if is_authorized:
                # 🟢 GREEN BOX - AUTHORIZED/MATCHED FACE
                box_color = (0, 255, 0)  # GREEN in BGR
                label_bg_color = (0, 200, 0)
                label_text_color = (255, 255, 255)
                
                # Draw thick green box
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), box_color, 4)
                
                # Get user information
                match_id = match_info.get('match_id', 'UNKNOWN')
                confidence = match_info.get('confidence', 0.0)
                
                # Draw "AUTHORIZED" label at top
                auth_text = "✓ AUTHORIZED"
                (text_w, text_h), _ = cv2.getTextSize(auth_text, cv2.FONT_HERSHEY_DUPLEX, 0.7, 2)
                cv2.rectangle(display_frame, (x1, y1-35), (x1 + text_w + 10, y1), label_bg_color, -1)
                cv2.putText(display_frame, auth_text, (x1 + 5, y1-10), 
                           cv2.FONT_HERSHEY_DUPLEX, 0.7, label_text_color, 2)
                
                # Draw ID and name at bottom
                if match_info.get('user_info'):
                    user_info = match_info['user_info']
                    name_text = f"{user_info.first_name} {user_info.last_name}"
                    id_text = f"ID: {match_id}"
                    bottom_text = f"{name_text} ({int(confidence*100)}%)"
                    
                    (name_w, name_h), _ = cv2.getTextSize(bottom_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(display_frame, (x1, y2+5), (x1 + name_w + 10, y2+32), label_bg_color, -1)
                    cv2.putText(display_frame, bottom_text, (x1 + 5, y2+24), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, label_text_color, 2)
                else:
                    # Just show ID if no user info
                    id_text = f"ID: {match_id} ({int(confidence*100)}%)"
                    (id_w, id_h), _ = cv2.getTextSize(id_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(display_frame, (x1, y2+5), (x1 + id_w + 10, y2+32), label_bg_color, -1)
                    cv2.putText(display_frame, id_text, (x1 + 5, y2+24), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, label_text_color, 2)
                
                print(f"🟢 Drawn GREEN box for: {match_id}")
                
            else:
                # 🔴 RED BOX - UNAUTHORIZED/UNKNOWN FACE
                box_color = (0, 0, 255)  # RED in BGR
                label_bg_color = (0, 0, 200)
                label_text_color = (255, 255, 255)
                
                # Draw thick red box
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), box_color, 4)
                
                # Draw "UNAUTHORIZED" label
                unauth_text = "✗ UNAUTHORIZED"
                (text_w, text_h), _ = cv2.getTextSize(unauth_text, cv2.FONT_HERSHEY_DUPLEX, 0.7, 2)
                cv2.rectangle(display_frame, (x1, y1-35), (x1 + text_w + 10, y1), label_bg_color, -1)
                cv2.putText(display_frame, unauth_text, (x1 + 5, y1-10), 
                           cv2.FONT_HERSHEY_DUPLEX, 0.7, label_text_color, 2)
                
                # Show "Unknown Person" at bottom
                unknown_text = "Unknown Person"
                (unk_w, unk_h), _ = cv2.getTextSize(unknown_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(display_frame, (x1, y2+5), (x1 + unk_w + 10, y2+32), label_bg_color, -1)
                cv2.putText(display_frame, unknown_text, (x1 + 5, y2+24), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, label_text_color, 2)
                
                print(f"🔴 Drawn RED box for unknown face")
        
        return display_frame
    
    def _smooth_face_boxes(self, current_locations, camera_id):
        """Apply temporal smoothing to face box coordinates to reduce flickering"""
        if not current_locations:
            return current_locations
        
        if camera_id not in self._stable_boxes:
            self._stable_boxes[camera_id] = []
        
        # Keep last 3 frames for smoothing
        self._stable_boxes[camera_id].append(current_locations)
        if len(self._stable_boxes[camera_id]) > 3:
            self._stable_boxes[camera_id].pop(0)
        
        if len(self._stable_boxes[camera_id]) == 1:
            return current_locations
        
        # Calculate smoothed positions
        smoothed_locations = []
        for i in range(len(current_locations)):
            if i < len(current_locations):
                # Get coordinates from recent frames
                recent_coords = []
                for frame_data in self._stable_boxes[camera_id]:
                    if i < len(frame_data):
                        recent_coords.append(frame_data[i])
                
                if recent_coords:
                    # Average the coordinates for stability
                    x1_avg = int(sum(coord[0] for coord in recent_coords) / len(recent_coords))
                    y1_avg = int(sum(coord[1] for coord in recent_coords) / len(recent_coords))
                    x2_avg = int(sum(coord[2] for coord in recent_coords) / len(recent_coords))
                    y2_avg = int(sum(coord[3] for coord in recent_coords) / len(recent_coords))
                    
                    smoothed_locations.append((x1_avg, y1_avg, x2_avg, y2_avg))
                else:
                    smoothed_locations.append(current_locations[i])
            
        return smoothed_locations
    
    def get_frame_generator(self, camera_id):
        """Generate frames for HTTP streaming with stability and fast loading support"""
        initialization_timeout = 30  # Wait up to 30 seconds for camera initialization
        start_time = time.time()
        
        while self.running:
            try:
                # Check if camera frame queue exists and has frames
                if camera_id in self.frame_queues and not self.frame_queues[camera_id].empty():
                    frame = self.frame_queues[camera_id].get(timeout=1.0)
                    
                    # Encode with good quality
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                    
                elif camera_id in self.frame_queues:
                    # Frame queue exists but is empty - camera is initializing
                    if time.time() - start_time < initialization_timeout:
                        # Generate a loading frame
                        loading_frame = self._generate_stable_no_signal_frame(camera_id)
                        _, buffer = cv2.imencode('.jpg', loading_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        
                        yield (b'--frame\r\n'
                              b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                        
                        time.sleep(0.1)  # Slower rate while initializing
                    else:
                        # Timeout - camera failed to initialize
                        error_frame = self._generate_error_frame(camera_id, "Initialization timeout")
                        _, buffer = cv2.imencode('.jpg', error_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        
                        yield (b'--frame\r\n'
                              b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                        time.sleep(1.0)
                else:
                    # No frame queue - camera not initialized
                    init_frame = self._generate_stable_no_signal_frame(camera_id)
                    _, buffer = cv2.imencode('.jpg', init_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                    time.sleep(0.2)
                    
            except Exception as e:
                print(f"Error in frame generator for camera {camera_id}: {e}")
                
                # Generate error frame
                try:
                    error_frame = self._generate_error_frame(camera_id, str(e))
                    _, buffer = cv2.imencode('.jpg', error_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                except:
                    pass
                    
                time.sleep(0.5)
    
    def cleanup(self):
        """Clean up camera resources"""
        print("Cleaning up enhanced camera system...")
        
        self.running = False
        
        # Wait for threads to finish
        for thread in self.capture_threads.values():
            if thread.is_alive():
                thread.join(timeout=2)
        
        # Release cameras
        for camera_id, cap in self.cameras.items():
            if cap is not None:
                try:
                    cap.release()
                    print(f"Released camera {camera_id}")
                except Exception as e:
                    print(f"Error releasing camera {camera_id}: {e}")
        
        # Clear resources
        self.cameras.clear()
        self.frame_queues.clear()
        self.display_states.clear()
        self.capture_threads.clear()
        
        print("Enhanced camera system cleanup complete")
    
    def reload_face_embeddings(self):
        """Reload face embeddings (useful after new enrollment)"""
        try:
            self.matcher.load_embeddings()
            print("Face embeddings reloaded successfully")
            return True
        except Exception as e:
            print(f"Error reloading face embeddings: {e}")
            return False

    def _notify_unauthorized(self, camera_id: int):
        """Rate-limited notifier for unauthorized detections.

        Sends an SMS to the configured phone number if the last SMS for the
        system was sent more than `self._sms_cooldown` seconds ago (global cooldown).
        """
        try:
            now = time.time()
            last = getattr(self, '_last_sms_sent_global', 0)
            if now - last < self._sms_cooldown:
                # still within global cooldown
                return

            # Get admin contact number from database
            from ..models import SystemConfig
            recipient = SystemConfig.get_admin_contact()
            message = f"ISSC System\nUnauthorized Person detected in Camera {camera_id + 1}"

            # Dispatch asynchronously
            send_sms_async(recipient, message)

            # Update global last-sent timestamp
            self._last_sms_sent_global = now
        except Exception as e:
            print(f"_notify_unauthorized error: {e}")


# Global camera manager instance
enhanced_camera_manager = EnhancedCameraManager()


# Enhanced view functions
@login_required(login_url='/login/')
def enhanced_live_feed(request):
    """Enhanced live feed view with stable camera handling"""
    try:
        # Initialize the enhanced camera system
        enhanced_camera_manager.initialize_for_live_feed()
        
        # Get user info
        user = AccountRegistration.objects.filter(username=request.user).values().first()
        
        # Always provide exactly 4 camera IDs regardless of detection status
        camera_ids = [0, 1, 2, 3]
        
        print(f"Enhanced live feed showing 4 cameras: {camera_ids}")
        print(f"Detected cameras: {list(enhanced_camera_manager.cameras.keys())}")
        
        # Use the improved template
        template = loader.get_template('live-feed/live-feed-improved.html')
        
        context = {
            'user_role': user['privilege'] if user else 'unknown',
            'user_data': user if user else {},
            'camera_ids': camera_ids,
            'recording_status': "Active"  # You can add recording status logic here
        }
        
        return HttpResponse(template.render(context, request))
        
    except Exception as e:
        print(f"Error in enhanced_live_feed: {e}")
        # Fallback to basic template
        template = loader.get_template('live-feed/live-feed.html')
        context = {'camera_ids': [0], 'recording_status': 'Error'}
        return HttpResponse(template.render(context, request))


def enhanced_video_feed(request, camera_id):
    """Enhanced video feed with better stability and fast loading support"""
    try:
        camera_id = int(camera_id)
        
        # Ensure the camera manager is initialized
        if not enhanced_camera_manager.running:
            print(f"Camera manager not running, initializing for camera {camera_id}")
            enhanced_camera_manager.initialize_for_live_feed()
        
        # Check if camera exists or if it's still initializing
        if camera_id not in enhanced_camera_manager.cameras:
            print(f"Camera {camera_id} not found in manager, available cameras: {list(enhanced_camera_manager.cameras.keys())}")
            return HttpResponse(f"Camera {camera_id} not available", status=404)
        
        # Check if camera has a frame queue
        if camera_id not in enhanced_camera_manager.frame_queues:
            print(f"Camera {camera_id} frame queue not ready")
            return HttpResponse(f"Camera {camera_id} not ready", status=503)
        
        return StreamingHttpResponse(
            enhanced_camera_manager.get_frame_generator(camera_id),
            content_type='multipart/x-mixed-replace; boundary=frame'
        )
        
    except Exception as e:
        print(f"Error in enhanced_video_feed for camera {camera_id}: {e}")
        return HttpResponse("Camera error", status=500)