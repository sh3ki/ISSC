"""
ULTRA-FAST LIGHTNING CAMERA SYSTEM
SUB-2 SECOND LOADING TIME
SUPER OPTIMIZED for lightning-fast initialization
"""
import cv2
import numpy as np
import time
import threading
from queue import Queue, Empty
from django.http import StreamingHttpResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.template import loader
from threading import Thread, Lock
import json

class UltraFastCameraManager:
    """Ultra-fast camera manager optimized for SUB-2 second loading"""
    
    def __init__(self):
        self.cameras = {}
        self.frame_queues = {}
        self.running = False
        self.lock = Lock()
        self.initialized = False
        
        # ULTRA-FAST settings
        self.FRAME_WIDTH = 640
        self.FRAME_HEIGHT = 480
        self.FPS = 30
        self.BUFFER_SIZE = 1  # Minimal buffer for speed
        self.DETECTION_SKIP = 5  # Process every 5th frame for speed
        
        # Pre-load face detection
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Initialize face matching system
        self.face_matcher = None
        self._init_face_matcher()
        
        # Frame counters for detection optimization
        self.frame_counters = {0: 0, 1: 0, 2: 0, 3: 0}
    
    def _init_face_matcher(self):
        """Initialize face matching system"""
        try:
            from ..computer_vision.face_matching import FaceMatcher
            self.face_matcher = FaceMatcher()
            print("✅ Face matcher initialized - ULTRA FAST MODE")
        except Exception as e:
            print(f"⚠️ Face matcher initialization error: {e}")
            self.face_matcher = None
    
    def ultra_fast_camera_init(self):
        """ULTRA-FAST camera initialization in SUB-2 seconds"""
        if self.initialized:
            print("⚡ Camera system already initialized - INSTANT READY!")
            return
        
        start_time = time.time()
        print("🚀 ULTRA-FAST CAMERA INITIALIZATION STARTING...")
        
        with self.lock:
            # LIGHTNING detection of specific cameras
            detected = self._lightning_detect_cameras()
            
            # INSTANT assignment
            self.cameras = self._instant_camera_assignment(detected)
            
            # INSTANT queue setup
            self._instant_queue_setup()
            
            # INSTANT thread startup
            self._instant_thread_startup()
            
            self.running = True
            self.initialized = True
        
        total_time = time.time() - start_time
        working_cams = [k for k, v in self.cameras.items() if v is not None]
        
        print(f"⚡ ULTRA-FAST INIT COMPLETE in {total_time:.2f}s")
        print(f"🎯 Camera Status: {working_cams}")
        print(f"📺 Ready for SUB-2 second live feed!")
        
        return self.cameras
    
    def _lightning_detect_cameras(self):
        """Lightning-fast camera detection - ONLY test cameras 0 and 1"""
        print("⚡ Lightning camera detection - Testing 0 and 1 only...")
        detected = {}
        
        # Test Camera 0 (Acer HD user-facing)
        print("   🔍 Testing Camera 0 (Acer HD user-facing)...")
        try:
            cap0 = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if cap0.isOpened():
                ret, frame = cap0.read()
                if ret and frame is not None:
                    print("   ✅ Camera 0: Acer HD WORKING")
                    cap0.set(cv2.CAP_PROP_FRAME_WIDTH, self.FRAME_WIDTH)
                    cap0.set(cv2.CAP_PROP_FRAME_HEIGHT, self.FRAME_HEIGHT)
                    cap0.set(cv2.CAP_PROP_BUFFERSIZE, self.BUFFER_SIZE)
                    detected[0] = cap0
                else:
                    print("   ❌ Camera 0: Acer HD no frame")
                    cap0.release()
            else:
                print("   ❌ Camera 0: Acer HD cannot open")
                cap0.release()
        except Exception as e:
            print(f"   ❌ Camera 0: Acer HD error - {e}")
        
        time.sleep(0.1)  # Brief pause
        
        # Test Camera 1 (Rapoo camera)
        print("   🔍 Testing Camera 1 (Rapoo camera)...")
        try:
            cap1 = cv2.VideoCapture(1, cv2.CAP_DSHOW)
            if cap1.isOpened():
                ret, frame = cap1.read()
                if ret and frame is not None:
                    print("   ✅ Camera 1: Rapoo WORKING")
                    cap1.set(cv2.CAP_PROP_FRAME_WIDTH, self.FRAME_WIDTH)
                    cap1.set(cv2.CAP_PROP_FRAME_HEIGHT, self.FRAME_HEIGHT)
                    cap1.set(cv2.CAP_PROP_BUFFERSIZE, self.BUFFER_SIZE)
                    detected[1] = cap1
                else:
                    print("   ❌ Camera 1: Rapoo no frame")
                    cap1.release()
            else:
                print("   ❌ Camera 1: Rapoo cannot open")
                cap1.release()
        except Exception as e:
            print(f"   ❌ Camera 1: Rapoo error - {e}")
        
        return detected
    
    def _instant_camera_assignment(self, detected):
        """Instant camera assignment based on requirements"""
        assigned = {}
        
        # Camera 0: Acer HD user-facing camera
        if 0 in detected:
            assigned[0] = detected[0]
            print("🎯 Camera 0: Acer HD user-facing camera ASSIGNED")
        else:
            assigned[0] = None
            print("📵 Camera 0: Acer HD not available")
        
        # Camera 1: Rapoo camera
        if 1 in detected:
            assigned[1] = detected[1]
            print("🎯 Camera 1: Rapoo camera ASSIGNED")
        else:
            assigned[1] = None
            print("📵 Camera 1: Rapoo not available")
        
        # Camera 2 & 3: No input (as requested)
        assigned[2] = None
        assigned[3] = None
        print("📵 Camera 2: No input (as requested)")
        print("📵 Camera 3: No input (as requested)")
        
        return assigned
    
    def _instant_queue_setup(self):
        """Instant frame queue setup"""
        print("⚡ Setting up ultra-fast frame queues...")
        self.frame_queues = {}
        for camera_id in range(4):
            self.frame_queues[camera_id] = Queue(maxsize=2)  # Minimal queue size for speed
    
    def _instant_thread_startup(self):
        """Instant thread startup for all cameras"""
        print("🧵 Starting ultra-fast capture threads...")
        
        for camera_id in range(4):
            if self.cameras[camera_id] is not None:
                # Real camera thread
                thread = Thread(target=self._ultra_fast_capture_loop, args=(camera_id,), daemon=True)
                thread.start()
                print(f"🟢 Ultra-fast thread started for Camera {camera_id}")
            else:
                # No input thread
                thread = Thread(target=self._no_input_loop, args=(camera_id,), daemon=True)
                thread.start()
                print(f"⚫ No-input thread started for Camera {camera_id}")
    
    def _ultra_fast_capture_loop(self, camera_id):
        """Ultra-fast capture loop with optimized face detection"""
        cap = self.cameras[camera_id]
        print(f"🎬 Starting capture loop for Camera {camera_id}")
        
        frame_count = 0
        while self.running:
            try:
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    frame_count += 1
                    if frame_count % 30 == 0:  # Log every 30 frames
                        print(f"📸 Camera {camera_id}: {frame_count} frames captured")
                    
                    # OPTIMIZED face detection - only every Nth frame
                    self.frame_counters[camera_id] += 1
                    if self.frame_counters[camera_id] % self.DETECTION_SKIP == 0:
                        frame = self._ultra_fast_face_detection(frame, camera_id)
                    
                    # ULTRA-FAST queue management
                    try:
                        if self.frame_queues[camera_id].full():
                            self.frame_queues[camera_id].get_nowait()  # Drop old frame
                        self.frame_queues[camera_id].put_nowait(frame)
                    except Exception as queue_error:
                        print(f"Queue error camera {camera_id}: {queue_error}")
                else:
                    print(f"⚠️ Camera {camera_id}: Failed to read frame (ret={ret})")
                    # Camera disconnected - show NO INPUT
                    no_input_frame = self._generate_no_input_frame(camera_id)
                    try:
                        if not self.frame_queues[camera_id].full():
                            self.frame_queues[camera_id].put_nowait(no_input_frame)
                    except:
                        pass
                    time.sleep(0.5)  # Wait longer on failed reads
                
                time.sleep(1/self.FPS)  # Maintain frame rate
                
            except Exception as e:
                print(f"❌ Capture error camera {camera_id}: {e}")
                # Put a NO INPUT frame on error
                try:
                    no_input_frame = self._generate_no_input_frame(camera_id)
                    if not self.frame_queues[camera_id].full():
                        self.frame_queues[camera_id].put_nowait(no_input_frame)
                except:
                    pass
                time.sleep(0.5)
    
    def _ultra_fast_face_detection(self, frame, camera_id):
        """Ultra-fast face detection with green/red boxes"""
        try:
            # FAST detection on smaller image
            small_frame = cv2.resize(frame, (320, 240))
            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
            
            # Fast cascade detection
            faces = self.face_cascade.detectMultiScale(gray, 1.2, 3, minSize=(20, 20))
            
            # Scale back to original frame size
            scale_x = frame.shape[1] / 320
            scale_y = frame.shape[0] / 240
            
            for (x, y, w, h) in faces:
                # Scale coordinates back
                x1 = int(x * scale_x)
                y1 = int(y * scale_y)
                x2 = int((x + w) * scale_x)
                y2 = int((y + h) * scale_y)
                
                # FAST face matching
                is_authorized = False
                match_id = "UNKNOWN"
                
                if self.face_matcher is not None:
                    try:
                        # Extract face region
                        face_roi = frame[y1:y2, x1:x2]
                        
                        # FAST embedding extraction
                        face_embedding = self.face_matcher.extract_embedding_fast(face_roi)
                        if face_embedding is not None:
                            # FAST matching
                            match_id, confidence = self.face_matcher.match_fast(face_embedding)
                            if match_id and confidence > 0.6:
                                is_authorized = True
                    except:
                        pass  # Skip on any error for speed
                
                # Draw boxes - GREEN for authorized, RED for unauthorized
                if is_authorized:
                    # GREEN box for authorized
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    label = f"ID: {match_id}"
                    cv2.rectangle(frame, (x1, y1-25), (x1 + 100, y1), (0, 255, 0), -1)
                    cv2.putText(frame, label, (x1 + 5, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
                else:
                    # RED box for unauthorized
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    label = "UNAUTHORIZED"
                    cv2.rectangle(frame, (x1, y1-25), (x1 + 120, y1), (0, 0, 255), -1)
                    cv2.putText(frame, label, (x1 + 5, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        except Exception as e:
            pass  # Skip errors for maximum speed
        
        return frame
    
    def _no_input_loop(self, camera_id):
        """Loop for cameras showing NO INPUT"""
        no_input_frame = self._generate_no_input_frame(camera_id)
        
        while self.running:
            try:
                if not self.frame_queues[camera_id].full():
                    self.frame_queues[camera_id].put_nowait(no_input_frame.copy())
                time.sleep(1.0)  # Slower refresh for static content
            except:
                time.sleep(0.1)
    
    def _generate_no_input_frame(self, camera_id):
        """Generate NO INPUT frame"""
        frame = np.zeros((self.FRAME_HEIGHT, self.FRAME_WIDTH, 3), dtype=np.uint8)
        frame[:] = (30, 30, 30)  # Dark gray background
        
        # NO INPUT text
        cv2.putText(frame, "NO INPUT", (200, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (100, 100, 100), 3)
        cv2.putText(frame, f"Camera {camera_id}", (240, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 150), 2)
        
        return frame
    
    def get_ultra_fast_frame(self, camera_id):
        """Get frame with ultra-fast retrieval"""
        try:
            if camera_id in self.frame_queues:
                if not self.frame_queues[camera_id].empty():
                    frame = self.frame_queues[camera_id].get_nowait()
                    # print(f"🎞️ Camera {camera_id}: Got frame from queue")
                    return frame
                else:
                    print(f"📭 Camera {camera_id}: Queue empty, returning NO INPUT")
                    return self._generate_no_input_frame(camera_id)
            else:
                print(f"❌ Camera {camera_id}: Queue not found")
                return self._generate_no_input_frame(camera_id)
        except Empty:
            print(f"📭 Camera {camera_id}: Queue empty (Empty exception)")
            return self._generate_no_input_frame(camera_id)
        except Exception as e:
            print(f"❌ Camera {camera_id}: Frame retrieval error - {e}")
            return self._generate_no_input_frame(camera_id)

# Global ultra-fast camera manager
ultra_fast_manager = UltraFastCameraManager()

@login_required(login_url='/login/')
def ultra_fast_live_feed(request):
    """ULTRA-FAST Live Feed - SUB-2 Second Loading"""
    try:
        print("🚀 ULTRA-FAST Live Feed accessed!")
        
        # INSTANT initialization
        ultra_fast_manager.ultra_fast_camera_init()
        
        # Get user info
        from ..models import AccountRegistration
        user = AccountRegistration.objects.filter(username=request.user).values().first()
        
        # Use original live-feed template for standard UI
        template = loader.get_template('live-feed/live-feed.html')
        context = {
            'user_role': user['privilege'] if user else 'unknown',
            'camera_ids': [0, 1, 2, 3],  # Always show 4 cameras
            'system_name': 'Ultra-Fast Live Feed',
            'recording_status': 'LIGHTNING ACTIVE'  # Add status for original template
        }
        
        print("⚡ ULTRA-FAST Live Feed ready!")
        return HttpResponse(template.render(context, request))
        
    except Exception as e:
        print(f"❌ Ultra-fast live feed error: {e}")
        return HttpResponse(f"System Error: {str(e)}", status=500)

def ultra_fast_video_feed(request, camera_id):
    """Ultra-fast video feed endpoint"""
    try:
        camera_id = int(camera_id)
        
        # Ensure system is initialized
        if not ultra_fast_manager.initialized:
            ultra_fast_manager.ultra_fast_camera_init()
        
        def generate_ultra_fast_frames():
            while True:
                try:
                    frame = ultra_fast_manager.get_ultra_fast_frame(camera_id)
                    
                    # FAST JPEG encoding
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                    
                    time.sleep(1/30)  # 30 FPS
                except Exception as e:
                    print(f"Frame generation error: {e}")
                    time.sleep(0.1)
        
        return StreamingHttpResponse(
            generate_ultra_fast_frames(),
            content_type='multipart/x-mixed-replace; boundary=frame'
        )
        
    except Exception as e:
        print(f"❌ Ultra-fast video feed error: {e}")
        return HttpResponse(f"Video Error: {str(e)}", status=500)