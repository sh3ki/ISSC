"""
LIGHTNING-FAST CAMERA SYSTEM
Optimized for sub-5 second initialization with full face detection
"""
import cv2
import numpy as np
import time
import threading
from queue import Queue
from django.http import StreamingHttpResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.template import loader
from threading import Thread, Lock
import json

class LightningCameraManager:
    """Ultra-fast camera manager optimized for speed"""
    
    def __init__(self):
        self.cameras = {}
        self.frame_queues = {}
        self.running = False
        self.lock = Lock()
        
        # Speed-optimized settings
        self.FRAME_WIDTH = 640
        self.FRAME_HEIGHT = 480
        self.FPS = 30
        self.DETECTION_INTERVAL = 3  # Process every 3rd frame for speed
        
        # Face detection optimization
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Initialize face matching system
        self.face_matcher = None
        self._init_face_matcher()
    
    def _init_face_matcher(self):
        """Initialize face matching system"""
        try:
            from ..computer_vision.face_matching import FaceMatcher
            self.face_matcher = FaceMatcher()
            print("Face matcher initialized successfully")
        except Exception as e:
            print(f"Face matcher initialization error: {e}")
            self.face_matcher = None
    
    def detect_cameras_fast(self):
        """Lightning-fast camera detection with intelligent assignment"""
        start_time = time.time()
        print("🚀 Starting lightning-fast camera detection...")
        print("🔍 Scanning ALL available cameras...")
        
        # Step 1: Discover ALL cameras with detailed info
        all_detected_cameras = {}
        camera_info = {}
        
        def test_camera_detailed(test_id):
            try:
                print(f"   Testing camera index {test_id}...")
                cap = cv2.VideoCapture(test_id, cv2.CAP_DSHOW)
                
                if cap.isOpened():
                    # Get camera name/info if possible
                    backend_name = cap.getBackendName() if hasattr(cap, 'getBackendName') else "Unknown"
                    
                    # Rapid configuration for speed
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.FRAME_WIDTH)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.FRAME_HEIGHT)
                    cap.set(cv2.CAP_PROP_FPS, self.FPS)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    
                    # Quick test - 2 frames for speed
                    success_count = 0
                    for _ in range(2):
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            success_count += 1
                    
                    if success_count >= 1:
                        # Try to identify camera type
                        camera_name = f"Camera_{test_id}"
                        
                        # Store detailed info
                        all_detected_cameras[test_id] = cap
                        camera_info[test_id] = {
                            'name': camera_name,
                            'backend': backend_name,
                            'status': 'WORKING'
                        }
                        
                        print(f"   ✅ Camera {test_id}: {camera_name} ({backend_name}) - WORKING")
                        return True
                    else:
                        cap.release()
                        print(f"   ❌ Camera {test_id}: Failed frame test")
                else:
                    cap.release()
                    print(f"   ❌ Camera {test_id}: Cannot open")
            except Exception as e:
                print(f"   ❌ Camera {test_id}: Error - {e}")
            
            return False
        
        # Test cameras 0-5 sequentially (using proven working method)
        print("📡 Testing camera indices 0-5 sequentially...")
        for test_id in range(6):  # Test 0-5 only
            print(f"   🔍 Testing camera {test_id}...")
            try:
                # Use DSHOW backend (same as working test)
                cap = cv2.VideoCapture(test_id, cv2.CAP_DSHOW)
                
                if cap.isOpened():
                    # Test frame capture (same as working test)
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        print(f"   ✅ Camera {test_id}: WORKING (frame captured)")
                        
                        # Configure camera AFTER confirming it works
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.FRAME_WIDTH)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.FRAME_HEIGHT)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        
                        # Store working camera (DON'T release it!)
                        all_detected_cameras[test_id] = cap
                        camera_info[test_id] = {
                            'name': f"Camera_{test_id}",
                            'backend': 'DSHOW',
                            'status': 'WORKING'
                        }
                    else:
                        print(f"   ❌ Camera {test_id}: No frame captured")
                        cap.release()
                else:
                    print(f"   ❌ Camera {test_id}: Cannot open")
                    if cap:
                        cap.release()
                    
            except Exception as e:
                print(f"   ❌ Camera {test_id}: Exception - {e}")
                try:
                    if 'cap' in locals():
                        cap.release()
                except:
                    pass
            
            # Small delay to prevent conflicts
            time.sleep(0.3)
        
        print(f"\n📋 CAMERA DETECTION RESULTS:")
        print(f"   Total cameras found: {len(all_detected_cameras)}")
        
        # Step 2: Smart camera assignment
        assigned_cameras = {}
        available_cameras = list(all_detected_cameras.keys())
        
        print(f"\n🎯 INTELLIGENT CAMERA ASSIGNMENT:")
        
        # Filter out NVIDIA/OBS cameras (usually higher indices or specific names)
        filtered_cameras = []
        excluded_cameras = []
        
        for cam_id in available_cameras:
            # Exclude typically virtual cameras (adjust as needed)
            if cam_id >= 8:  # Usually virtual cameras are at higher indices
                excluded_cameras.append(cam_id)
                print(f"   🚫 Excluding Camera {cam_id} (likely virtual camera)")
            else:
                filtered_cameras.append(cam_id)
        
        print(f"   📷 Physical cameras: {filtered_cameras}")
        print(f"   🚫 Excluded cameras: {excluded_cameras}")
        
        # Smart assignment logic based on YOUR requirements
        print(f"   🔍 Raw detected cameras: {list(all_detected_cameras.keys())}")
        
        # YOUR SPECIFIC REQUIREMENTS:
        # - Camera 0: Acer built-in (index 0)
        # - Camera 1: External webcam (index 1) 
        # - Camera 2 & 3: No input if no other cameras
        
        # Check if Camera 0 (Acer built-in) works
        if 0 in all_detected_cameras:
            assigned_cameras[0] = all_detected_cameras[0]
            print(f"   🎯 Camera 0: Acer built-in camera (index 0) - WORKING")
        else:
            assigned_cameras[0] = None
            print(f"   📵 Camera 0: Acer built-in camera not detected")
        
        # Check if Camera 1 (External webcam) works
        if 1 in all_detected_cameras:
            assigned_cameras[1] = all_detected_cameras[1]
            print(f"   🎯 Camera 1: External webcam (index 1) - WORKING")
        else:
            assigned_cameras[1] = None
            print(f"   📵 Camera 1: External webcam not detected")
        
        # Camera 2 & 3: Look for any other working cameras (exclude NVIDIA/OBS)
        other_cameras = []
        for cam_id in all_detected_cameras.keys():
            if cam_id not in [0, 1] and cam_id < 6:  # Exclude high indices (virtual cameras)
                other_cameras.append(cam_id)
        
        # Assign Camera 2
        if len(other_cameras) >= 1:
            assigned_cameras[2] = all_detected_cameras[other_cameras[0]]
            print(f"   🎯 Camera 2: Additional camera (index {other_cameras[0]}) - WORKING")
        else:
            assigned_cameras[2] = None
            print(f"   📵 Camera 2: No input (no additional cameras)")
        
        # Assign Camera 3
        if len(other_cameras) >= 2:
            assigned_cameras[3] = all_detected_cameras[other_cameras[1]]
            print(f"   🎯 Camera 3: Additional camera (index {other_cameras[1]}) - WORKING")
        else:
            assigned_cameras[3] = None
            print(f"   📵 Camera 3: No input (no additional cameras)")
        
        # Clean up excluded cameras
        for cam_id in excluded_cameras:
            if cam_id in all_detected_cameras:
                all_detected_cameras[cam_id].release()
        
        detection_time = time.time() - start_time
        real_cameras = [k for k, v in assigned_cameras.items() if v is not None]
        
        print(f"\n⚡ FINAL ASSIGNMENT COMPLETE in {detection_time:.2f}s")
        print(f"   Active cameras: {real_cameras}")
        print(f"   Camera layout: [0: {'✅' if assigned_cameras[0] else '❌'}, 1: {'✅' if assigned_cameras[1] else '❌'}, 2: {'✅' if assigned_cameras[2] else '❌'}, 3: {'✅' if assigned_cameras[3] else '❌'}]")
        
        # If no cameras detected, create test message
        if not real_cameras:
            print("⚠️  NO PHYSICAL CAMERAS DETECTED!")
            print("💡 This could be due to:")
            print("   - cameras in use by another app")
            print("   - driver issues") 
            print("   - NVIDIA virtual cameras interfering")
            print("   - permissions issues")
            print("🎯 Will show 'NO INPUT' for all camera slots")
        
        return assigned_cameras
    
    def initialize_lightning_fast(self):
        """Initialize entire system in under 5 seconds"""
        try:
            if self.running:
                print("⚡ System already running!")
                return
            
            start_time = time.time()
            print("🚀 LIGHTNING INITIALIZATION STARTING...")
            
            with self.lock:
                # Step 1: Detect cameras (target: 2 seconds)
                print("🔍 Starting camera detection...")
                self.cameras = self.detect_cameras_fast()
                print(f"📷 Camera detection complete: {list(self.cameras.keys())}")
                
                # Step 2: Initialize frame queues instantly
                print("🗂️ Initializing frame queues...")
                self.frame_queues = {}
                for camera_id in self.cameras:
                    self.frame_queues[camera_id] = Queue(maxsize=2)
                
                # Step 3: Start capture threads immediately
                print("🧵 Starting capture threads...")
                self.running = True
                for camera_id, cap in self.cameras.items():
                    if cap is not None:
                        thread = Thread(target=self._lightning_capture_loop, args=(camera_id,), daemon=True)
                        thread.start()
                        print(f"🟢 Started capture thread for camera {camera_id}")
                    else:
                        thread = Thread(target=self._no_input_loop, args=(camera_id,), daemon=True)
                        thread.start()
                        print(f"⚫ Started no-input thread for camera {camera_id}")
            
            total_time = time.time() - start_time
            print(f"⚡ LIGHTNING INITIALIZATION COMPLETE in {total_time:.2f}s")
            
        except Exception as e:
            print(f"❌ Lightning initialization error: {e}")
            import traceback
            print(f"❌ Full traceback: {traceback.format_exc()}")
            self.running = False
            raise e
    
    def _lightning_capture_loop(self, camera_id):
        """Ultra-fast capture loop with optimized face detection"""
        cap = self.cameras[camera_id]
        frame_count = 0
        
        while self.running:
            try:
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    # Process face detection every nth frame for speed
                    if frame_count % self.DETECTION_INTERVAL == 0:
                        frame = self._fast_face_detection(frame, camera_id)
                    
                    # Queue management for speed
                    if self.frame_queues[camera_id].full():
                        try:
                            self.frame_queues[camera_id].get_nowait()
                        except:
                            pass
                    
                    self.frame_queues[camera_id].put(frame)
                    frame_count += 1
                else:
                    # Camera disconnected - show NO INPUT
                    no_input_frame = self._generate_no_input_frame(camera_id)
                    if not self.frame_queues[camera_id].full():
                        self.frame_queues[camera_id].put(no_input_frame)
                
                time.sleep(1/self.FPS)
                
            except Exception as e:
                print(f"Capture error camera {camera_id}: {e}")
                no_input_frame = self._generate_no_input_frame(camera_id)
                if not self.frame_queues[camera_id].full():
                    self.frame_queues[camera_id].put(no_input_frame)
                time.sleep(0.1)
    
    def _no_input_loop(self, camera_id):
        """Loop for cameras showing NO INPUT"""
        no_input_frame = self._generate_no_input_frame(camera_id)
        
        while self.running:
            try:
                if not self.frame_queues[camera_id].full():
                    self.frame_queues[camera_id].put(no_input_frame.copy())
                time.sleep(1.0)  # Slower refresh for static content
            except:
                time.sleep(0.1)
    
    def _fast_face_detection(self, frame, camera_id):
        """Optimized face detection with green/red boxes"""
        try:
            # Resize for speed
            small_frame = cv2.resize(frame, (320, 240))
            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
            
            # Fast face detection
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(30, 30))
            
            # Scale back to original frame size
            scale_x = frame.shape[1] / 320
            scale_y = frame.shape[0] / 240
            
            for (x, y, w, h) in faces:
                # Scale coordinates
                x1 = int(x * scale_x)
                y1 = int(y * scale_y)
                x2 = int((x + w) * scale_x)
                y2 = int((y + h) * scale_y)
                
                # Extract face for matching
                face_roi = frame[y1:y2, x1:x2]
                
                # Face matching
                is_authorized = False
                match_id = None
                
                if self.face_matcher and face_roi.shape[0] > 20 and face_roi.shape[1] > 20:
                    try:
                        # Quick face matching
                        embedding = self.face_matcher.extract_embedding_fast(face_roi)
                        if embedding is not None:
                            match_id, confidence = self.face_matcher.match_fast(embedding)
                            is_authorized = match_id is not None and confidence > 0.7
                    except:
                        pass
                
                # Draw boxes - GREEN for authorized, RED for unauthorized
                if is_authorized:
                    # GREEN box for authorized
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # ID label
                    label = f"ID: {match_id}"
                    cv2.rectangle(frame, (x1, y1-25), (x1 + 100, y1), (0, 255, 0), -1)
                    cv2.putText(frame, label, (x1 + 5, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
                else:
                    # RED box for unauthorized
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    
                    # UNAUTHORIZED label
                    label = "UNAUTHORIZED"
                    cv2.rectangle(frame, (x1, y1-25), (x1 + 120, y1), (0, 0, 255), -1)
                    cv2.putText(frame, label, (x1 + 5, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        except Exception as e:
            print(f"Face detection error: {e}")
        
        return frame
    
    def _generate_no_input_frame(self, camera_id):
        """Generate NO INPUT frame"""
        frame = np.zeros((self.FRAME_HEIGHT, self.FRAME_WIDTH, 3), dtype=np.uint8)
        frame[:] = (30, 30, 30)  # Dark gray background
        
        # NO INPUT text
        cv2.putText(frame, "NO INPUT", (200, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (100, 100, 100), 3)
        cv2.putText(frame, f"Camera {camera_id}", (240, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 150), 2)
        
        return frame
    
    def get_frame_generator(self, camera_id):
        """Lightning-fast frame generator"""
        while self.running:
            try:
                if camera_id in self.frame_queues and not self.frame_queues[camera_id].empty():
                    frame = self.frame_queues[camera_id].get(timeout=0.1)
                    
                    # Fast JPEG encoding
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                else:
                    time.sleep(0.01)
            except Exception as e:
                print(f"Frame generator error for camera {camera_id}: {e}")
                time.sleep(0.1)
    
    def cleanup(self):
        """Fast cleanup"""
        print("🔥 Lightning cleanup starting...")
        self.running = False
        
        for camera_id, cap in self.cameras.items():
            if cap is not None:
                try:
                    cap.release()
                except:
                    pass
        
        self.cameras.clear()
        self.frame_queues.clear()
        print("🔥 Lightning cleanup complete")

# Global lightning camera manager
lightning_camera_manager = LightningCameraManager()

def lightning_live_feed(request):
    """Lightning-fast live feed view"""
    try:
        print("🚀 Lightning live feed accessed!")
        print("🔧 Initializing lightning-fast camera system...")
        
        # Initialize lightning-fast system
        lightning_camera_manager.initialize_lightning_fast()
        
        print("✅ Lightning camera system initialized successfully")
        
        # Get user info quickly
        from ..models import AccountRegistration
        user = AccountRegistration.objects.filter(username=request.user).values().first()
        
        # Always show 4 cameras
        camera_ids = [0, 1, 2, 3]
        
        template = loader.get_template('live-feed/lightning-live-feed.html')
        context = {
            'user_role': user['privilege'] if user else 'unknown',
            'camera_ids': camera_ids,
            'system_name': 'Lightning Live Feed'
        }
        
        print("📄 Template loaded, rendering response...")
        return HttpResponse(template.render(context, request))
        
    except Exception as e:
        print(f"❌ Lightning live feed error: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        return HttpResponse(f"System Error: {str(e)}", status=500)

def lightning_video_feed(request, camera_id):
    """Lightning-fast video feed endpoint"""
    try:
        camera_id = int(camera_id)
        
        # Ensure system is initialized
        if not lightning_camera_manager.running:
            lightning_camera_manager.initialize_lightning_fast()
        
        # Check if camera exists
        if camera_id not in lightning_camera_manager.cameras:
            return HttpResponse("Camera not found", status=404)
        
        return StreamingHttpResponse(
            lightning_camera_manager.get_frame_generator(camera_id),
            content_type='multipart/x-mixed-replace; boundary=frame'
        )
        
    except Exception as e:
        print(f"Lightning video feed error for camera {camera_id}: {e}")
        return HttpResponse("Feed Error", status=500)