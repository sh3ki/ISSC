"""
ISSC Face Recognition Views
API endpoints for real-time face recognition in live feed
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json
from main.computer_vision.face_recognition_engine import face_engine
from main.models import FaceLogs, AccountRegistration, UnauthorizedFaceDetection
import base64
import cv2
import numpy as np
import os
from datetime import datetime
from django.conf import settings


@csrf_exempt
@require_http_methods(["POST"])
def recognize_faces_api(request):
    """
    Ultra-fast face recognition API
    Receives face embeddings and returns recognition results
    """
    try:
        data = json.loads(request.body)
        face_embeddings = data.get('face_embeddings', [])
        
        if not face_embeddings:
            return JsonResponse({'error': 'No face embeddings provided'}, status=400)
        
        # Recognize all faces
        results = face_engine.recognize_multiple_faces(face_embeddings)
        
        return JsonResponse({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        print(f"❌ Error in recognize_faces_api: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def record_face_log_api(request):
    """
    Record face log when authorized face is detected
    """
    try:
        data = json.loads(request.body)
        id_number = data.get('id_number')
        
        if not id_number:
            return JsonResponse({'error': 'Missing id_number'}, status=400)
        
        # Get user from database
        try:
            user = AccountRegistration.objects.get(id_number=id_number)
        except AccountRegistration.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        
        # Check if there's already a log for this user in the last 2 seconds to avoid duplicates
        from datetime import timedelta
        recent_threshold = timezone.now() - timedelta(seconds=2)
        recent_log = FaceLogs.objects.filter(
            id_number=user,
            created_at__gte=recent_threshold
        ).first()
        
        if recent_log:
            # Don't create duplicate log
            return JsonResponse({
                'success': True,
                'message': 'Log already exists (cooldown)',
                'is_duplicate': True
            })
        
        # Create face log
        face_log = FaceLogs.objects.create(
            id_number=user,
            first_name=user.first_name,
            middle_name=user.middle_name,
            last_name=user.last_name
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Face log recorded for {user.first_name} {user.last_name}',
            'log_id': str(face_log.id),
            'is_duplicate': False
        })
        
    except Exception as e:
        print(f"❌ Error in record_face_log_api: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def save_unauthorized_face_api(request):
    """
    Save unauthorized face detection
    """
    try:
        data = json.loads(request.body)
        image_data = data.get('image')
        camera_box_id = data.get('camera_box_id', 0)
        notes = data.get('notes')
        
        if not image_data:
            return JsonResponse({'error': 'No image data provided'}, status=400)
        
        # Decode base64 image
        try:
            # Remove data URL prefix if present
            if 'base64,' in image_data:
                image_data = image_data.split('base64,')[1]
            
            # Decode base64
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return JsonResponse({'error': 'Failed to decode image'}, status=400)
            
        except Exception as e:
            print(f"❌ Error decoding image: {e}")
            return JsonResponse({'error': 'Invalid image data'}, status=400)
        
        # Create unauthorized_faces directory if it doesn't exist
        date_folder = datetime.now().strftime('%Y-%m-%d')
        unauthorized_dir = os.path.join(settings.MEDIA_ROOT, 'unauthorized_faces', date_folder)
        os.makedirs(unauthorized_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f'unauthorized_cam{camera_box_id}_{timestamp}.jpg'
        filepath = os.path.join(unauthorized_dir, filename)
        
        # Save image
        saved = cv2.imwrite(filepath, img)
        if not saved or not os.path.exists(filepath):
            return JsonResponse({'error': 'Failed to save image to disk'}, status=500)
        
        # Save to database
        relative_path = os.path.join('unauthorized_faces', date_folder, filename)
        detection = UnauthorizedFaceDetection.objects.create(
            image_path=relative_path,
            camera_box_id=camera_box_id,
            notes=notes
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Unauthorized face saved',
            'detection_id': str(detection.detection_id),
            'image_path': relative_path
        })
        
    except Exception as e:
        print(f"❌ Error in save_unauthorized_face_api: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
