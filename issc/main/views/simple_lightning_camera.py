"""
SIMPLIFIED LIGHTNING CAMERA SYSTEM - NO CRASHES
Working version that properly detects Camera 1
"""
import cv2
import numpy as np
import time
from django.http import StreamingHttpResponse, HttpResponse
from django.template import loader

class SimpleLightningCameraManager:
    """Simplified camera manager that works"""
    
    def __init__(self):
        self.cameras = {}
        self.initialized = False
        
        # Face detection
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Face matching
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
    
    def detect_and_assign_cameras(self):
        """Detect cameras and assign them properly - AVOID NVIDIA CAMERAS"""
        print("🚀 COMPLETE LIGHTNING CAMERA DETECTION")
        
        # Test ONLY cameras 0-1 to avoid NVIDIA virtual camera conflicts
        detected = {}
        for cam_id in range(2):  # Only test 0 and 1
            print(f"   Testing camera {cam_id}...")
            try:
                cap = cv2.VideoCapture(cam_id, cv2.CAP_DSHOW)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        print(f"   ✅ Camera {cam_id}: WORKING")
                        # Configure camera
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        detected[cam_id] = cap
                    else:
                        print(f"   ❌ Camera {cam_id}: No frame")
                        cap.release()
                else:
                    print(f"   ❌ Camera {cam_id}: Cannot open")
                    cap.release()
            except Exception as e:
                print(f"   ❌ Camera {cam_id}: Error - {e}")
            
            time.sleep(0.3)  # Longer delay for stability
        
        # Assignment based on YOUR requirements
        assigned = {}
        
        # Camera 0: Acer built-in (index 0)
        if 0 in detected:
            assigned[0] = detected[0]
            print("🎯 Camera 0: Acer built-in (index 0) assigned")
        else:
            assigned[0] = None
            print("📵 Camera 0: Acer built-in not found")
        
        # Camera 1: External webcam (index 1)
        if 1 in detected:
            assigned[1] = detected[1]
            print("🎯 Camera 1: External webcam (index 1) assigned")
        else:
            assigned[1] = None
            print("📵 Camera 1: External webcam not found")
        
        # Camera 2 & 3: Additional or No Input
        other_cams = [k for k in detected.keys() if k not in [0, 1]]
        
        if len(other_cams) >= 1:
            assigned[2] = detected[other_cams[0]]
            print(f"🎯 Camera 2: Additional camera (index {other_cams[0]}) assigned")
        else:
            assigned[2] = None
            print("📵 Camera 2: No input")
        
        if len(other_cams) >= 2:
            assigned[3] = detected[other_cams[1]]
            print(f"🎯 Camera 3: Additional camera (index {other_cams[1]}) assigned")
        else:
            assigned[3] = None
            print("📵 Camera 3: No input")
        
        # Clean up unassigned cameras
        for cam_id, cap in detected.items():
            if cap not in assigned.values():
                cap.release()
        
        self.cameras = assigned
        self.initialized = True
        
        working = [k for k, v in assigned.items() if v is not None]
        print(f"⚡ CAMERA ASSIGNMENT COMPLETE - Working: {working}")
        
        return assigned
    
    def get_frame(self, camera_id):
        """Get single frame from camera"""
        if camera_id not in self.cameras:
            return self._generate_no_input_frame(camera_id)
        
        cap = self.cameras[camera_id]
        if cap is None:
            return self._generate_no_input_frame(camera_id)
        
        try:
            ret, frame = cap.read()
            if ret and frame is not None:
                # Add face detection
                frame = self._add_face_detection(frame, camera_id)
                return frame
            else:
                return self._generate_no_input_frame(camera_id)
        except Exception as e:
            print(f"Frame capture error camera {camera_id}: {e}")
            return self._generate_no_input_frame(camera_id)
    
    def _add_face_detection(self, frame, camera_id):
        """Add complete face detection with green/red boxes"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(30, 30))
            
            for (x, y, w, h) in faces:
                # Extract face for matching
                face_roi = frame[y:y+h, x:x+w]
                is_authorized = False
                match_id = "UNKNOWN"
                
                # Face matching using face_matcher
                if self.face_matcher is not None:
                    try:
                        # Extract face embedding first
                        face_embedding = self.face_matcher.extract_embedding_fast(face_roi)
                        if face_embedding is not None:
                            # Use face matcher to identify person
                            match_id, confidence = self.face_matcher.match_fast(face_embedding)
                            if match_id and confidence > 0.6:  # Confidence threshold
                                is_authorized = True
                                print(f"✅ Face match: {match_id} (confidence: {confidence:.2f})")
                            else:
                                print(f"⚠️ Low confidence or no match: {confidence:.2f}")
                    except Exception as e:
                        print(f"Face matching error: {e}")
                
                # Draw boxes based on authorization
                if is_authorized:
                    # GREEN box for authorized (ID matches)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
                    
                    # ID label with green background
                    label = f"ID: {match_id}"
                    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                    cv2.rectangle(frame, (x, y-30), (x + label_size[0] + 10, y), (0, 255, 0), -1)
                    cv2.putText(frame, label, (x + 5, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
                    
                    print(f"🟢 Camera {camera_id}: Authorized person detected - {match_id}")
                else:
                    # RED box for unauthorized
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 3)
                    
                    # UNAUTHORIZED label with red background
                    label = "UNAUTHORIZED"
                    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                    cv2.rectangle(frame, (x, y-30), (x + label_size[0] + 10, y), (0, 0, 255), -1)
                    cv2.putText(frame, label, (x + 5, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                    print(f"🔴 Camera {camera_id}: Unauthorized person detected")
                
        except Exception as e:
            print(f"Face detection error: {e}")
        
        return frame
    
    def _generate_no_input_frame(self, camera_id):
        """Generate NO INPUT frame"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (30, 30, 30)
        
        cv2.putText(frame, "NO INPUT", (220, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (100, 100, 100), 3)
        cv2.putText(frame, f"Camera {camera_id}", (260, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 150), 2)
        
        return frame

# Global instance
simple_lightning_manager = SimpleLightningCameraManager()

def simple_lightning_live_feed(request):
    """Simple lightning live feed view"""
    try:
        print("🚀 Simple Lightning Live Feed accessed")
        
        # Initialize if needed
        if not simple_lightning_manager.initialized:
            simple_lightning_manager.detect_and_assign_cameras()
        
        template = loader.get_template('live-feed/lightning-live-feed.html')
        context = {
            'user_role': 'admin',  # Simplified
            'camera_ids': [0, 1, 2, 3],
            'system_name': 'Simple Lightning Live Feed'
        }
        
        return HttpResponse(template.render(context, request))
        
    except Exception as e:
        print(f"❌ Simple lightning error: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return HttpResponse(f"Error: {str(e)}", status=500)

def simple_lightning_video_feed(request, camera_id):
    """Simple lightning video feed"""
    try:
        camera_id = int(camera_id)
        
        def generate_frames():
            while True:
                try:
                    frame = simple_lightning_manager.get_frame(camera_id)
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                    
                    time.sleep(1/30)  # 30 FPS
                except Exception as e:
                    print(f"Frame generation error: {e}")
                    time.sleep(0.1)
        
        return StreamingHttpResponse(
            generate_frames(),
            content_type='multipart/x-mixed-replace; boundary=frame'
        )
        
    except Exception as e:
        print(f"❌ Video feed error: {e}")
        return HttpResponse(f"Video Error: {str(e)}", status=500)