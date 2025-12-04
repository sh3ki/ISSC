import cv2
import threading
import numpy as np
import hashlib
import time
import os
import base64
import json

from django.views.decorators import gzip
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required

from ..models import AccountRegistration, FacesEmbeddings
from ..computer_vision.face_enrollment import FaceEnrollment

# Lazy-load face enrollment to avoid conflicts with live-feed FaceNet
# Only initialize when actually needed for face enrollment
face_enrollment = None


def get_face_enrollment():
    """Lazy-load FaceEnrollment instance only when needed"""
    global face_enrollment
    if face_enrollment is None:
        print("🎭 Initializing FaceEnrollment for face enrollment page...")
        face_enrollment = FaceEnrollment(device='cuda')
    return face_enrollment


def generate_face_feed():
    """⚡ LIGHTNING FAST face detection for enrollment - Haar Cascade only, NO embedding comparison"""
    from .video_feed_view import face_cameras, face_cam_id
    
    # ⚡ Initialize SUPER FAST Haar Cascade (no deep learning, pure speed!)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    while True:
        try:
            # Check if face camera is available and initialized
            if face_cameras and face_cam_id in face_cameras and face_cameras[face_cam_id] is not None:
                cap = face_cameras[face_cam_id]
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    # ⚡ LIGHTNING FAST but ACCURATE face detection
                    # Convert to grayscale for SPEED
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    
                    # ⚡ Detect faces - FAST but ACCURATE (stricter parameters)
                    faces = face_cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.15,      # More accurate (was 1.1)
                        minNeighbors=6,        # Less false positives (was 4)
                        minSize=(60, 60),      # Larger minimum face size (was 30x30)
                        flags=cv2.CASCADE_SCALE_IMAGE
                    )
                    
                    # ⚡ Filter out non-faces using aspect ratio check
                    valid_faces = []
                    for (x, y, w, h) in faces:
                        # Check if aspect ratio is face-like (width/height should be ~0.75-1.3)
                        aspect_ratio = w / h if h > 0 else 0
                        if 0.7 <= aspect_ratio <= 1.4:  # Reasonable face proportions
                            # Check if face is not too small or too large
                            face_area = w * h
                            frame_area = frame.shape[0] * frame.shape[1]
                            if 0.01 <= (face_area / frame_area) <= 0.6:  # 1% to 60% of frame
                                valid_faces.append((x, y, w, h))
                    
                    # ⚡ Draw bounding boxes - INSTANT
                    annotated_frame = frame.copy()
                    for (x, y, w, h) in valid_faces:
                        # Draw GREEN box (for enrollment, all detected faces are "good")
                        cv2.rectangle(annotated_frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
                        
                        # Add simple label
                        cv2.putText(annotated_frame, "Face Detected", (x, y-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    # Add face count
                    cv2.putText(annotated_frame, f"Faces: {len(valid_faces)}", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    
                    # ⚡ Fast JPEG encoding (quality 85 for speed)
                    _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                else:
                    # Camera read failed, yield a blank frame
                    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(blank_frame, "Camera not available", (150, 240), 
                              cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    _, buffer = cv2.imencode('.jpg', blank_frame)
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            else:
                # No camera available, yield a placeholder frame
                blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(blank_frame, "Please select a camera", (150, 220), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
                cv2.putText(blank_frame, "and click 'Initialize Camera'", (120, 260), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
                _, buffer = cv2.imencode('.jpg', blank_frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                       
            time.sleep(0.016)  # ⚡ 60 FPS target (faster than 30 FPS)
            
        except Exception as e:
            print(f"Error in face feed generation: {e}")
            # Yield error frame
            error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(error_frame, "Camera Error", (200, 240), 
                      cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            _, buffer = cv2.imencode('.jpg', error_frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(1)


def face_video_feed(request):
    return StreamingHttpResponse(generate_face_feed(),
                                  content_type='multipart/x-mixed-replace; boundary=frame')


def handle_base64_image(data):
    try:
        if not data.startswith("data:image"):
            raise ValueError("Base64 string does not have an image prefix.")
        
        format, imgstr = data.split(';base64,')
        img_data = base64.b64decode(imgstr)
        img_array = np.frombuffer(img_data, dtype=np.uint8)
        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("cv2.imdecode failed: image is None.")
        
        return image

    except Exception as e:
        print(f"[handle_base64_image] Error decoding image: {e}")
        return None


@login_required(login_url='/login')
def face_enrollment_view(request, id_number):
    # Handle camera selection for face enrollment
    selected_camera_id = None
    
    # Check for camera parameter in request
    if request.method == "POST":
        try:
            if request.content_type == 'application/json':
                body = json.loads(request.body)
                selected_camera_id = body.get('camera_id')
            else:
                selected_camera_id = request.POST.get('camera_id')
        except:
            pass
    
    if not selected_camera_id:
        selected_camera_id = request.GET.get('camera')
    
    # Convert to int if it's a valid number
    if selected_camera_id is not None:
        try:
            selected_camera_id = int(selected_camera_id)
        except (ValueError, TypeError):
            selected_camera_id = None
    
    # Only initialize camera if user has selected one
    if selected_camera_id is not None:
        # Initialize camera specifically for face enrollment with selected camera
        from .video_feed_view import initialize_face_enrollment_camera
        initialize_face_enrollment_camera(selected_camera_id)
        
        # If this is a POST request for camera initialization (without image data), return success
        if request.method == "POST" and 'front_image' not in request.POST:
            return JsonResponse({'success': True, 'message': f'Camera {selected_camera_id} initialized for face enrollment'})
    
    print("Request Method:", request.method)
    print("User:", request.user)

    user_privilege = AccountRegistration.objects.filter(username=request.user).values()
    print("User Privilege QuerySet:", list(user_privilege))

    user = get_object_or_404(AccountRegistration, id_number=id_number)
    print("User Retrieved:", user)

    if request.method == "POST" and 'front_image' in request.POST:
        front_image = request.POST.get('front_image')
        left_image = request.POST.get('left_image')
        right_image = request.POST.get('right_image')

        print("Front Image (truncated):", front_image[:50] if front_image else "None")
        print("Left Image (truncated):", left_image[:50] if left_image else "None")
        print("Right Image (truncated):", right_image[:50] if right_image else "None")

        if front_image and left_image and right_image:
            try:
                front_img = handle_base64_image(front_image)
                left_img = handle_base64_image(left_image)
                right_img = handle_base64_image(right_image)

                print("Decoded Front Image Shape:", front_img.shape if front_img is not None else "None")
                print("Decoded Left Image Shape:", left_img.shape if left_img is not None else "None")
                print("Decoded Right Image Shape:", right_img.shape if right_img is not None else "None")
                
                # Make sure all images are contiguous for better GPU processing
                if front_img is not None:
                    front_img = np.ascontiguousarray(front_img)
                if left_img is not None:
                    left_img = np.ascontiguousarray(left_img)
                if right_img is not None:
                    right_img = np.ascontiguousarray(right_img)

                enrollment = get_face_enrollment()
                front_faces, _ = enrollment.detect_faces(front_img)
                left_faces, _ = enrollment.detect_faces(left_img)
                right_faces, _ = enrollment.detect_faces(right_img)

                print("Front Faces Detected:", len(front_faces) if front_faces else 0)
                print("Left Faces Detected:", len(left_faces) if left_faces else 0)
                print("Right Faces Detected:", len(right_faces) if right_faces else 0)

                if (front_faces and len(front_faces) == 1 and 
                    left_faces and len(left_faces) == 1 and 
                    right_faces and len(right_faces) == 1):
                    
                    # FIXED: Changed method name from get_face_embedding to extract_embeddings
                    front_embedding = enrollment.extract_embeddings(front_faces[0])
                    left_embedding = enrollment.extract_embeddings(left_faces[0])
                    right_embedding = enrollment.extract_embeddings(right_faces[0])

                    print("Front Embedding Type:", type(front_embedding))
                    print("Front Embedding Shape:", front_embedding.shape if front_embedding is not None else "None")
                    
                    # Verify embeddings are different (128-dim for DeepFace Facenet model)
                    if front_embedding is not None and left_embedding is not None and right_embedding is not None:
                        # Check correct size (128-dim for Facenet, 512-dim for Facenet512)
                        expected_dims = [128, 512]  # Accept both Facenet variants
                        if front_embedding.shape[0] not in expected_dims:
                            print(f"⚠️ WARNING: Unexpected embedding size: {front_embedding.shape[0]} (expected {expected_dims})")
                        
                        front_left_dist = np.linalg.norm(front_embedding - left_embedding)
                        front_right_dist = np.linalg.norm(front_embedding - right_embedding)
                        left_right_dist = np.linalg.norm(left_embedding - right_embedding)
                        
                        print(f"🔍 Embedding distances - Front-Left: {front_left_dist:.4f}, Front-Right: {front_right_dist:.4f}, Left-Right: {left_right_dist:.4f}")
                        
                        # Check if embeddings are suspiciously similar (same image captured 3 times)
                        if front_left_dist < 0.01 and front_right_dist < 0.01:
                            print("⚠️ WARNING: All 3 embeddings are nearly identical - same frame captured!")
                            return render(request, 'face_enrollment/error.html', {
                                'message': 'All three images appear to be identical! Please ensure you turn your head to the left and right before capturing each angle.',
                                'user_role': user_privilege[0]['privilege'] if user_privilege else 'Unknown',
                            })
                        
                        print("✅ Embeddings are different - good capture!")

                    if front_embedding is not None and left_embedding is not None and right_embedding is not None:
                        # FIXED: Store as JSON serializable lists instead of strings
                        # Check if there's an existing embedding for this user and update it
                        FacesEmbeddings.objects.update_or_create(
                            id_number=user,
                            defaults={
                                'front_embedding': front_embedding.tolist(),
                                'left_embedding': left_embedding.tolist(),
                                'right_embedding': right_embedding.tolist(),
                            }
                        )
                        print(f"Embeddings stored for user {id_number}")

                        print("Embeddings saved successfully.")
                        
                        # IMPORTANT: Refresh face embeddings in the live feed system
                        try:
                            from .video_feed_view import matcher
                            from .enhanced_video_feed import enhanced_camera_manager
                            
                            # Reload embeddings in the original matcher
                            matcher.load_embeddings()
                            print("Original face matcher embeddings refreshed")
                            
                            # Reload embeddings in the enhanced camera manager
                            enhanced_camera_manager.reload_face_embeddings()
                            print("Enhanced camera manager embeddings refreshed")
                            
                            # Ensure simple live feed cache picks up the new embeddings immediately
                            try:
                                from . import live_feed_simple
                                live_feed_simple.load_face_embeddings()
                                print("Simple live feed embeddings refreshed")
                            except Exception as refresh_err:
                                print(f"Warning: Could not refresh simple live feed embeddings: {refresh_err}")
                            
                        except Exception as e:
                            print(f"Warning: Could not refresh live feed embeddings: {e}")

                        return render(request, 'face_enrollment/success_page.html', {
                            "front_faces": front_image,
                            "left_faces": left_image,
                            "right_faces": right_image,
                            "user_role": user_privilege[0]['privilege'] if user_privilege else 'Unknown',
                        })
                    else:
                        print("Error: One or more embeddings are None.")
                        return render(request, 'face_enrollment/error.html', {
                            'message': 'Failed to extract embeddings for one or more images.',
                            'user_role': user_privilege[0]['privilege'] if user_privilege else 'Unknown',
                        })
                else:
                    print("Error: Incorrect number of faces detected.")
                    return render(request, 'face_enrollment/error.html', {
                        'message': 'Exactly one face must be detected in each image. Please try again.',
                        'user_role': user_privilege[0]['privilege'] if user_privilege else 'Unknown',
                    })

            except Exception as e:
                print("Exception occurred:", e)
                return render(request, 'face_enrollment/error.html', {
                    'message': f'Error processing images: {e}',
                    'user_role': user_privilege[0]['privilege'] if user_privilege else 'Unknown',
                })
        else:
            print("Error: One or more image inputs are missing.")
            return render(request, 'face_enrollment/error.html', {
                'message': 'Missing image data! Please capture all three face angles.',
                'user_role': user_privilege[0]['privilege'] if user_privilege else 'Unknown',
            })

    print("Rendering initial face enrollment form.")
    return render(request, 'face_enrollment/faceenrollment.html', {
        'user_role': user_privilege[0]['privilege'] if user_privilege else 'Unknown',
        'user_data': user,
        'camera_ids': range(5),
    })


@login_required(login_url='/login')
def enrollee_view(request):
    user_privilege = AccountRegistration.objects.filter(username=request.user).values()
    user_data = AccountRegistration.objects.all()

    enrolled_ids = FacesEmbeddings.objects.values_list('id_number', flat=True)

    return render(request, 'face_enrollment/enrollee.html', {
        'user_role': user_privilege[0]['privilege'] if user_privilege else 'Unknown',
        'user_data': user_data,
        'camera_ids': range(5),
        'enrolled_ids': list(enrolled_ids),  # Convert QuerySet to list for template
    })


@login_required(login_url='/login')
def success_page(request):
    user_privilege = AccountRegistration.objects.filter(username=request.user).values()
    return render(request, 'face_enrollment/success_page.html', {
        'user_role': user_privilege[0]['privilege'] if user_privilege else 'Unknown',
    })


def error_page(request):
    user_privilege = AccountRegistration.objects.filter(username=request.user).values()
    return render(request, 'face_enrollment/error.html', {
        'user_role': user_privilege[0]['privilege'] if user_privilege else 'Unknown',
    })