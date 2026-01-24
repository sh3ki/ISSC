"""
Live Feed View with Simple Face Recognition
Multi-threaded face recognition using DeepFace library
"""

from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.template import loader
from ..models import (
    AccountRegistration,
    FacesEmbeddings,
    UnauthorizedFaceDetection,
    FaceLogs,
)
import cv2
from threading import Thread, Lock
from queue import Queue
import time
import numpy as np
# Lazy import DeepFace to avoid TensorFlow loading at startup
# from deepface import DeepFace
_deepface_module = None

def get_deepface():
    """Lazy-load DeepFace only when needed"""
    global _deepface_module
    if _deepface_module is None:
        from deepface import DeepFace
        _deepface_module = DeepFace
    return _deepface_module

import json
import os
from datetime import datetime
from django.conf import settings
from ..utils.philsms import send_sms_async, PHILSMS_DEFAULT_RECIPIENT
import platform

# DeepFace library with TensorFlow backend - reliable and well-maintained
print(f"✅ Face Recognition using DeepFace library (TensorFlow backend)")

# Store active cameras for live feed
live_feed_cameras = {}  # {box_id: camera_object}
live_feed_queues = {}   # {box_id: Queue for processed frames}
live_feed_threads = {}  # {box_id: capture thread}
face_recognition_threads = {}  # {box_id: recognition thread}
raw_frame_queues = {}  # {box_id: Queue for raw frames before processing}

# Face embeddings cache (loaded from database)
face_embeddings_cache = {}  # {id_number: {'embeddings': [...], 'name': str}}
face_embeddings_lock = Lock()

# Unauthorized face tracking (per camera box)
unauthorized_last_save = {}  # {box_id: timestamp of last save}
unauthorized_save_lock = Lock()
authorized_last_save = {}  # {(box_id, id_number): timestamp}
authorized_save_lock = Lock()


def find_camera_index_by_label(target_label):
    """Best-effort mapping of a browser camera label to a Windows DirectShow index."""
    if not target_label:
        return None

    # Only attempt this on Windows where DirectShow device order is available
    if platform.system().lower() != 'windows':
        return None

    try:
        from pygrabber.dshow_graph import FilterGraph

        graph = FilterGraph()
        devices = graph.get_input_devices()  # Ordered as DirectShow presents them
        target_lower = target_label.lower()

        for idx, name in enumerate(devices):
            if target_lower in name.lower():
                print(f"🔎 Matched camera label '{target_label}' to DirectShow device '{name}' at index {idx}")
                return idx

        print(f"⚠️ No DirectShow device matched label '{target_label}'. Devices: {devices}")
    except ImportError:
        print("⚠️ pygrabber not installed; skipping DirectShow camera label mapping. Run `pip install pygrabber` to enable precise mapping.")
    except Exception as e:
        print(f"⚠️ Could not enumerate DirectShow devices: {e}")

    return None

# Recognition settings
RECOGNITION_THRESHOLD = 0.45  # Cosine distance threshold (smaller = more similar)
FRAME_SKIP = 2  # Process every Nth frame for speed (1 = all frames, 2 = every other frame)
UNAUTHORIZED_SAVE_INTERVAL = 2.0  # Save unauthorized face every 2 seconds
SAVE_UNAUTHORIZED_FACES = True  # Save unmatched faces when a valid face is detected


def normalize_embedding(embedding):
    """Return L2-normalized embedding vector."""
    if embedding is None:
        return None

    if not isinstance(embedding, np.ndarray):
        embedding = np.array(embedding, dtype=np.float64)

    norm = np.linalg.norm(embedding)
    if norm == 0:
        return None

    return embedding / norm


def load_face_embeddings():
    """Load all face embeddings from database into memory for fast lookup"""
    global face_embeddings_cache
    
    with face_embeddings_lock:
        try:
            print("=" * 80)
            print("📚 LOADING FACE EMBEDDINGS FROM DATABASE")
            print("=" * 80)
            
            embeddings = FacesEmbeddings.objects.all()
            face_embeddings_cache = {}
            
            loaded_count = 0
            error_count = 0
            
            print(f"Found {embeddings.count()} face embedding record(s) in database")
            print("-" * 80)
            
            for emb in embeddings:
                try:
                    # Get account info
                    id_num = emb.id_number.id_number if hasattr(emb.id_number, 'id_number') else str(emb.id_number)
                    account = AccountRegistration.objects.filter(id_number=id_num).first()
                    name = f"{account.first_name} {account.last_name}" if account else "Unknown"
                    
                    print(f"\n📋 Processing embedding for: {id_num} ({name})")
                    
                    # Load all three embeddings (front, left, right) as 128-dim numpy arrays
                    embeddings_to_try = [
                        ('front_embedding', emb.front_embedding),
                        ('left_embedding', emb.left_embedding),
                        ('right_embedding', emb.right_embedding)
                    ]
                    
                    loaded_embeddings = []
                    
                    for emb_name, emb_data in embeddings_to_try:
                        try:
                            # Handle different data formats
                            if isinstance(emb_data, str):
                                embedding_list = json.loads(emb_data)
                            elif isinstance(emb_data, list):
                                embedding_list = emb_data
                            elif isinstance(emb_data, dict):
                                print(f"   ⚠️ {emb_name}: Empty (not captured)")
                                continue
                            else:
                                print(f"   ⚠️ {emb_name}: Unknown format {type(emb_data)}")
                                continue
                            
                            if embedding_list and len(embedding_list) > 0:
                                embedding_array = normalize_embedding(embedding_list)
                                if embedding_array is not None:
                                    loaded_embeddings.append(embedding_array)
                                    print(f"   ✅ {emb_name}: Loaded successfully (shape: {embedding_array.shape})")
                                else:
                                    print(f"   ⚠️ {emb_name}: Normalization failed")
                            else:
                                print(f"   ⚠️ {emb_name}: Empty list")
                        
                        except Exception as e:
                            print(f"   ❌ {emb_name}: Error - {e}")
                    
                    # Store ALL embeddings (front, left, right) for better matching
                    if loaded_embeddings:
                        face_embeddings_cache[id_num] = {
                            'embeddings': loaded_embeddings,
                            'name': name
                        }
                        loaded_count += 1
                        print(f"   🎯 CACHED {len(loaded_embeddings)} embedding(s) for {id_num}")
                    else:
                        error_count += 1
                        print(f"   ❌ NO VALID EMBEDDINGS found for {id_num}")
                
                except Exception as e:
                    error_count += 1
                    print(f"   ❌ CRITICAL ERROR processing {id_num}: {e}")
                    import traceback
                    traceback.print_exc()
            
            print("=" * 80)
            print(f"✅ FACE EMBEDDINGS LOADING COMPLETE")
            print(f"   Total records processed: {embeddings.count()}")
            print(f"   Successfully loaded: {loaded_count}")
            print(f"   Errors: {error_count}")
            print(f"   Cache size: {len(face_embeddings_cache)} person(s)")
            print("=" * 80)
            return True
            
        except Exception as e:
            print("=" * 80)
            print(f"❌ CRITICAL ERROR LOADING FACE EMBEDDINGS: {e}")
            import traceback
            traceback.print_exc()
            print("=" * 80)
            return False


def recognize_face(face_embedding, log_details=False):
    """
    Match face embedding against database using ALL stored embeddings (front, left, right)
    Uses face_recognition library distance calculation (Euclidean)
    Returns: (id_number, name, distance) or (None, None, None)
    """
    face_embedding = normalize_embedding(face_embedding)
    if face_embedding is None:
        return None, None, None

    if len(face_embeddings_cache) == 0:
        if log_details:
            print("⚠️ No embeddings in cache to compare against")
        return None, None, None
    
    min_distance = float('inf')
    matched_id = None
    matched_name = None
    
    # Compare with all cached embeddings
    for id_number, data in face_embeddings_cache.items():
        # Compare against ALL stored embeddings (front, left, right)
        # Use the MINIMUM distance across all angles for better matching
        embeddings_list = data['embeddings']  # List of numpy arrays
        
        distances_for_person = []
        for stored_embedding in embeddings_list:
            if stored_embedding is None:
                continue
            cosine_similarity = np.dot(face_embedding, stored_embedding)
            cosine_similarity = np.clip(cosine_similarity, -1.0, 1.0)
            cosine_distance = 1.0 - cosine_similarity
            distances_for_person.append(cosine_distance)

        if not distances_for_person:
            continue

        best_distance = min(distances_for_person)
        
        if best_distance < min_distance:
            min_distance = best_distance
            matched_id = id_number
            matched_name = data['name']
    
    # Check if match is within threshold
    if min_distance is not None and min_distance < RECOGNITION_THRESHOLD:
        return matched_id, matched_name, min_distance
    else:
        return None, None, min_distance


def is_valid_face_detection(facial_area, frame_shape):
    """Filter out tiny or invalid detections to avoid saving non-face data."""
    if not facial_area:
        return False

    w = facial_area.get('w', 0)
    h = facial_area.get('h', 0)
    if w <= 0 or h <= 0:
        return False

    # Reject very small detections (noise) and extremely large detections (likely false)
    if w < 60 or h < 60:
        return False

    frame_h, frame_w = frame_shape[:2]
    face_area = w * h
    frame_area = max(frame_h * frame_w, 1)
    area_ratio = face_area / frame_area
    if area_ratio < 0.01 or area_ratio > 0.5:
        return False

    aspect_ratio = w / max(h, 1)
    if aspect_ratio < 0.6 or aspect_ratio > 1.6:
        return False

    return True


def save_unauthorized_face(frame, box_id, facial_area):
    """
    Save unauthorized face image to disk and database
    Only saves once every 2 seconds per camera to avoid spam
    
    Args:
        frame: The full frame (BGR format)
        box_id: Camera box ID
        facial_area: Dict with x, y, w, h coordinates
    """
    global unauthorized_last_save
    
    if not SAVE_UNAUTHORIZED_FACES:
        # User explicitly requested not to save unauthorized faces.
        return

    if not is_valid_face_detection(facial_area, frame.shape):
        # Detection is not reliable, skip saving.
        return

    current_time = time.time()

    with unauthorized_save_lock:
        last_save = unauthorized_last_save.get(box_id, 0)
        if current_time - last_save < UNAUTHORIZED_SAVE_INTERVAL:
            return

        unauthorized_last_save[box_id] = current_time
    
    try:
        # Create directory structure: media/unauthorized_faces/YYYY-MM-DD/
        date_folder = datetime.now().strftime('%Y-%m-%d')
        save_dir = os.path.join(settings.MEDIA_ROOT, 'unauthorized_faces', date_folder)
        os.makedirs(save_dir, exist_ok=True)
        
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime('%H-%M-%S-%f')
        filename = f"camera{box_id}_{timestamp}.jpg"
        file_path = os.path.join(save_dir, filename)
        
        # Extract face region with some padding
        x, y, w, h = facial_area['x'], facial_area['y'], facial_area['w'], facial_area['h']
        padding = 20
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(frame.shape[1], x + w + padding)
        y2 = min(frame.shape[0], y + h + padding)
        
        # Crop face with padding
        face_crop = frame[y1:y2, x1:x2]
        
        # Save image to disk
        cv2.imwrite(file_path, face_crop)
        
        # Create relative path for database (relative to MEDIA_ROOT)
        relative_path = os.path.join('unauthorized_faces', date_folder, filename)
        
        # Save to database
        detection = UnauthorizedFaceDetection(
            image_path=relative_path,
            camera_box_id=box_id,
            notes=f"Detected at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        detection.save()
        print(f"💾 Saved unauthorized face: {relative_path}")

        # Dispatch SMS notification (async). philsms module enforces per-recipient cooldown.
        try:
            recipient = getattr(settings, 'PHILSMS_RECIPIENT', None)
            if not recipient:
                # Fallback to default recipient configured in philsms module
                recipient = PHILSMS_DEFAULT_RECIPIENT
            # Build a short message including camera info and saved path
            msg = f"ISSC System\nUnauthorized Person detected in Camera {box_id}\n{relative_path}"

            # If recipient is None, send_sms_async will use its own defaults if implemented
            if recipient:
                print(f"philsms: dispatching SMS to {recipient} for unauthorized detection (Box {box_id})")
                send_sms_async(recipient, msg)
            else:
                print(f"philsms: no recipient configured; skipping SMS for unauthorized detection (Box {box_id})")
        except Exception as e:
            print(f"philsms: error dispatching SMS for unauthorized detection: {e}")
        
    except Exception as e:
        print(f"⚠️ Error saving unauthorized face: {e}")


def log_authorized_face(box_id, matched_id):
    """Log authorized face detections to FaceLogs with throttling."""
    if not matched_id:
        return

    current_time = time.time()
    key = (str(box_id), str(matched_id))

    with authorized_save_lock:
        last_save = authorized_last_save.get(key, 0)
        if current_time - last_save < UNAUTHORIZED_SAVE_INTERVAL:
            return
        authorized_last_save[key] = current_time

    try:
        account = AccountRegistration.objects.filter(id_number=matched_id).first()
        if not account:
            print(f"⚠️ Cannot log authorized face. Account {matched_id} not found.")
            return

        FaceLogs.objects.create(
            id_number=account,
            first_name=account.first_name,
            middle_name=account.middle_name or '',
            last_name=account.last_name,
        )
        print(f"🟢 Logged authorized face: {matched_id} (Box {box_id})")
    except Exception as e:
        print(f"⚠️ Error logging authorized face {matched_id}: {e}")


def stop_live_feed_for_box(box_id):
    """Release resources associated with a specific live feed box."""
    box_key = str(box_id)

    if box_key not in live_feed_cameras and box_key not in raw_frame_queues:
        return False

    print(f"🛑 Releasing live feed resources for Box {box_key}")

    cap = live_feed_cameras.pop(box_key, None)
    if cap is not None:
        try:
            cap.release()
        except Exception as e:
            print(f"⚠️ Error releasing camera for Box {box_key}: {e}")

    live_feed_queues.pop(box_key, None)
    raw_frame_queues.pop(box_key, None)
    live_feed_threads.pop(box_key, None)
    face_recognition_threads.pop(box_key, None)

    return True


def stop_all_live_feed_cameras():
    """Release all active live feed cameras and associated resources."""
    active_boxes = list(set(
        list(live_feed_cameras.keys()) +
        list(raw_frame_queues.keys())
    ))

    stopped = []
    for box_id in active_boxes:
        if stop_live_feed_for_box(box_id):
            stopped.append(str(box_id))

    if stopped:
        print(f"🛑 Stopped live feed cameras for boxes: {', '.join(stopped)}")

    return stopped


def face_recognition_worker(box_id, camera_id):
    """
    Dedicated face recognition thread using face_recognition library
    Processes frames from raw_frame_queues and outputs annotated frames to live_feed_queues
    """
    print(f"🧠 Face recognition thread started for Box {box_id}, Camera {camera_id}")
    
    frame_count = 0
    recognition_count = 0
    
    # Loop until the box_id is removed from the global maps. Use
    # defensive `.get()` lookups inside the loop to avoid KeyError
    # if resources are removed concurrently by `stop_live_feed_for_box`.
    while True:
        try:
            # Re-check presence of resources each iteration
            raw_q = raw_frame_queues.get(box_id)
            out_q = live_feed_queues.get(box_id)
            cap = live_feed_cameras.get(box_id)

            # If any core resource is gone, exit loop cleanly
            if raw_q is None or out_q is None or cap is None:
                break

            # Get raw frame from queue (non-blocking)
            if raw_q.empty():
                time.sleep(0.01)
                continue

            frame = raw_q.get(timeout=0.1)
            frame_count += 1
            
            # Skip frames for speed (process every FRAME_SKIP frames)
            if frame_count % FRAME_SKIP != 0:
                # Pass through without processing
                if not live_feed_queues[box_id].full():
                    live_feed_queues[box_id].put(frame)
                continue
            
            # Convert to RGB for DeepFace
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            try:
                # Detect faces using DeepFace
                DeepFace = get_deepface()
                face_objs = DeepFace.extract_faces(
                    img_path=rgb_frame,
                    detector_backend='mtcnn',
                    enforce_detection=False,
                    align=True
                )
                
                # Process each detected face
                for face_obj in face_objs:
                    recognition_count += 1
                    
                    # Get facial area coordinates and validate
                    facial_area = face_obj.get('facial_area', {})
                    if not is_valid_face_detection(facial_area, frame.shape):
                        continue

                    x, y, w, h = facial_area['x'], facial_area['y'], facial_area['w'], facial_area['h']
                    
                    # Get face image for embedding extraction
                    face = face_obj['face']
                    
                    # DeepFace returns normalized float array [0,1], convert to uint8 [0,255]
                    if face.dtype == np.float32 or face.dtype == np.float64:
                        face = (face * 255).astype(np.uint8)
                    
                    # Extract embedding from detected face
                    try:
                        DeepFace = get_deepface()
                        result = DeepFace.represent(
                            img_path=face,
                            model_name='Facenet',
                            detector_backend='skip',  # Skip detection, already detected
                            enforce_detection=False,
                            align=False  # Already aligned
                        )
                        
                        if result and len(result) > 0:
                            face_embedding = normalize_embedding(result[0]['embedding'])
                            if face_embedding is None:
                                continue

                            # Recognize face
                            matched_id, matched_name, distance = recognize_face(face_embedding, log_details=False)
                            
                            # Draw bounding box and label
                            if matched_id:
                                # AUTHORIZED - Green box
                                color = (0, 255, 0)  # Green in BGR
                                label = f"ID: {matched_id}"
                                thickness = 3

                                # Log authorized detection with throttling
                                log_authorized_face(box_id, matched_id)
                            else:
                                # UNAUTHORIZED - Red box (no saving per user request)
                                color = (0, 0, 255)  # Red in BGR
                                label = "UNAUTHORIZED"
                                thickness = 3

                                # Save unauthorized face image (throttled)
                                save_unauthorized_face(frame, box_id, facial_area)
                            
                            # Draw rectangle
                            cv2.rectangle(frame, (x, y), (x+w, y+h), color, thickness)
                            
                            # Draw label background
                            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                            cv2.rectangle(frame, (x, y - label_size[1] - 10), 
                                         (x + label_size[0], y), color, -1)
                            
                            # Draw label text
                            cv2.putText(frame, label, (x, y - 5), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                            
                            # Draw confidence/distance
                            if distance is None or distance == float('inf'):
                                conf_text = "N/A"
                            else:
                                similarity = 1.0 - min(max(distance, 0.0), 1.0)
                                conf_text = f"{similarity:.2f}"
                            cv2.putText(frame, conf_text, (x, y+h+20), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                    
                    except Exception as embed_error:
                        print(f"⚠️ Error extracting embedding: {embed_error}")
                        continue
                        
            except Exception as detect_error:
                # If detection fails, just pass through the frame
                pass
            
            # Put processed frame in output queue if still available
            if out_q is not None and not out_q.full():
                out_q.put(frame)
        
        except Exception as e:
            print(f"⚠️ Error in face recognition for Box {box_id}: {e}")
            time.sleep(0.1)
    
    print(f"🛑 Face recognition thread stopped for Box {box_id}")


@login_required(login_url='/login/')
def live_feed_simple(request):
    """
    Live feed view with face recognition - PROTECH-style camera selection
    """
    # ALWAYS load face embeddings when page loads (this ensures new enrollments are picked up)
    print("📚 Loading face embeddings from database...")
    load_face_embeddings()
    
    user = AccountRegistration.objects.filter(username=request.user).values()
    
    template = loader.get_template('live-feed/live-feed-v2.html')
    
    context = {
        'user_role': user[0]['privilege'] if user else 'Unknown',
        'user_data': user[0] if user else None,
        'camera_ids': [0, 1, 2, 3],  # Default 4 camera boxes
        'recording_status': "Not Recording"  # Default status
    }
    
    return HttpResponse(template.render(context, request))


@login_required(login_url='/login/')
def recording_archive_simple(request):
    """
    Simple recording archive view - UI only
    """
    user = AccountRegistration.objects.filter(username=request.user).values()
    
    template = loader.get_template('live-feed/recording_arcihve.html')
    
    context = {
        'user_role': user[0]['privilege'] if user else 'Unknown',
        'user_data': user[0] if user else None,
        'recordings': []  # Empty for now - implement your logic here
    }
    
    return HttpResponse(template.render(context, request))


@login_required(login_url='/login/')
def face_logs_simple(request):
    """
    Display face log entries with pagination (20 per page) and search support
    """
    user = AccountRegistration.objects.filter(username=request.user).values()
    logs_queryset = FaceLogs.objects.select_related('id_number').order_by('-created_at')

    search_query = request.GET.get('q', '').strip()
    if search_query:
        logs_queryset = logs_queryset.filter(
            Q(first_name__icontains=search_query) |
            Q(middle_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(id_number__username__icontains=search_query)
        )

    paginator = Paginator(logs_queryset, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'user_role': user[0]['privilege'] if user else 'Unknown',
        'user_data': user[0] if user else None,
        'page_obj': page_obj,
        'logs': page_obj.object_list,
        'is_paginated': page_obj.has_other_pages(),
        'search_query': search_query,
    }

    return render(request, 'live-feed/face_logs.html', context)


def get_available_cameras_simple(request):
    """
    Simple API endpoint for available cameras with real device names
    """
    from .video_feed_view import get_available_cameras_info
    
    try:
        # Use the same function from video_feed_view to get real camera names
        cameras_info = get_available_cameras_info()
        return JsonResponse({'success': True, 'cameras': cameras_info})
    except Exception as e:
        print(f"Error getting cameras: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'cameras': []
        })


def video_feed_simple(request, camera_id):
    """
    Video feed endpoint - streams from initialized camera
    """
    from django.http import StreamingHttpResponse
    import numpy as np
    
    box_id = request.GET.get('box_id', None)
    
    def generate_frames(box_id):
        """Generate frames from camera or placeholder

        Re-check camera initialization on each iteration to avoid race
        where the camera is stopped concurrently and the queue/key
        is removed, which previously caused a KeyError.
        """
        while True:
            # Re-evaluate initialization state each loop to avoid stale value
            is_camera_initialized = box_id and box_id in live_feed_cameras and box_id in live_feed_queues

            if is_camera_initialized:
                # Camera is active - only show frames from queue, no placeholder
                q = live_feed_queues.get(box_id)
                if q is not None and not q.empty():
                    try:
                        frame = q.get(timeout=0.1)
                        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                    except Exception:
                        # On any error just continue the loop and re-check state
                        pass
                # If queue is empty but camera is active, just wait - don't show NO SIGNAL
                time.sleep(0.01)  # Short sleep to avoid busy waiting
            else:
                # Camera not initialized yet - show NO SIGNAL placeholder
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, "NO SIGNAL", (180, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
                cv2.putText(frame, f"Camera {camera_id}", (230, 280), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
                cv2.putText(frame, "", (150, 320), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)
                
                _, buffer = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                
                time.sleep(0.1)  # Slower refresh when showing placeholder
    
    return StreamingHttpResponse(
        generate_frames(box_id),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )


@login_required(login_url='/login/')
def initialize_live_feed_camera(request):
    """
    Initialize a specific camera for a specific box with face recognition
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})
    
    try:
        import json as json_module
        data = json_module.loads(request.body)
        box_id = str(data.get('box_id'))
        camera_id = int(data.get('camera_id'))
        camera_label = data.get('camera_label', '')
        device_id = data.get('device_id', '')
        
        print(f"🎬 Initializing camera for Box {box_id}:")
        print(f"   Requested camera_id: {camera_id}")
        print(f"   Camera label: {camera_label}")
        print(f"   Device ID: {device_id[:20]}...")
        
        # Note: Face embeddings are already loaded when live-feed page loaded
        # No need to check/load here
        
        # Stop existing camera for this box if any
        if box_id in live_feed_cameras and live_feed_cameras[box_id] is not None:
            print(f"🛑 Stopping existing camera for Box {box_id}")
            live_feed_cameras[box_id].release()
            live_feed_cameras[box_id] = None
        
        # Try to map by label first (Windows DirectShow)
        actual_camera_id = find_camera_index_by_label(camera_label)

        # If not found by label, try the provided index
        if actual_camera_id is None:
            print("🔍 Searching for a working camera index...")
            max_cameras_to_test = 10

            for test_id in range(max_cameras_to_test):
                test_cap = cv2.VideoCapture(test_id, cv2.CAP_DSHOW)
                if test_cap.isOpened():
                    ret, frame = test_cap.read()
                    if ret and frame is not None:
                        print(f"   ✓ Found working camera at index {test_id}")
                        if test_id == camera_id:
                            actual_camera_id = test_id
                            test_cap.release()
                            print(f"   ✅ Using requested camera index {actual_camera_id}")
                            break
                    test_cap.release()

        if actual_camera_id is None:
            # Fallback to the provided camera_id
            actual_camera_id = camera_id
            print(f"   ⚠️ Using fallback camera index {actual_camera_id}")
        
        # Open the selected camera
        cap = cv2.VideoCapture(actual_camera_id, cv2.CAP_DSHOW)
        
        # Set camera properties for optimal performance
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
        
        if not cap.isOpened():
            print(f"❌ Failed to open Camera {actual_camera_id}")
            return JsonResponse({
                'success': False,
                'error': f'Failed to open camera {actual_camera_id}'
            })
        
        # Test read a frame
        ret, frame = cap.read()
        if not ret or frame is None:
            print(f"❌ Camera {actual_camera_id} opened but cannot read frames")
            cap.release()
            return JsonResponse({
                'success': False,
                'error': f'Camera {actual_camera_id} cannot read frames'
            })
        
        # Store camera
        live_feed_cameras[box_id] = cap
        live_feed_queues[box_id] = Queue(maxsize=2)  # Processed frames
        raw_frame_queues[box_id] = Queue(maxsize=3)  # Raw frames before processing
        
        # Start frame capture thread (reads from camera, outputs to raw_frame_queue)
        def capture_frames(box_id, camera_id):
            print(f"📹 Frame capture thread started for Box {box_id}, Camera {camera_id} ({camera_label})")
            while True:
                try:
                    # Defensive lookups to avoid KeyError if the box is stopped
                    cap = live_feed_cameras.get(box_id)
                    raw_q = raw_frame_queues.get(box_id)

                    # If resources removed, exit loop gracefully
                    if cap is None or raw_q is None:
                        break

                    ret, frame = cap.read()
                    if ret and frame is not None:
                        # Put raw frame in queue for face recognition thread
                        try:
                            if raw_q.full():
                                try:
                                    raw_q.get_nowait()
                                except Exception:
                                    pass
                            raw_q.put(frame)
                        except Exception:
                            # If put fails, skip this frame
                            pass
                    else:
                        time.sleep(0.01)
                except Exception as e:
                    print(f"Error capturing frame for Box {box_id}: {e}")
                    time.sleep(0.1)
            print(f"🛑 Frame capture thread stopped for Box {box_id}")
        
        capture_thread = Thread(target=capture_frames, args=(box_id, actual_camera_id), daemon=True)
        capture_thread.start()
        live_feed_threads[box_id] = capture_thread

        # Start face recognition thread (reads from raw_frame_queue, processes, outputs to live_feed_queue)
        recognition_thread = Thread(target=face_recognition_worker, args=(box_id, actual_camera_id), daemon=True)
        recognition_thread.start()
        face_recognition_threads[box_id] = recognition_thread

        print(f"✅ Camera '{camera_label}' (index {actual_camera_id}) initialized successfully for Box {box_id}")

        return JsonResponse({
            'success': True,
            'message': f'Camera {actual_camera_id} initialized for Box {box_id}',
            'camera_id': actual_camera_id,
            'camera_label': camera_label
        })
        
    except Exception as e:
        print(f"❌ Error initializing camera: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required(login_url='/login/')
def stop_live_feed(request):
    """API endpoint to stop live feed cameras when user leaves the page."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})

    try:
        import json as json_module
        payload = request.body.decode('utf-8') or '{}'
        data = json_module.loads(payload)
        boxes = data.get('boxes')

        if boxes and isinstance(boxes, list):
            stopped = []
            for box_id in boxes:
                if stop_live_feed_for_box(box_id):
                    stopped.append(str(box_id))
        else:
            stopped = stop_all_live_feed_cameras()

        return JsonResponse({'success': True, 'stopped': stopped})

    except Exception as e:
        print(f"⚠️ Error stopping live feed: {e}")
        return JsonResponse({'success': False, 'error': str(e)})
