from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from ..computer_vision.face_matching import FaceMatcher
from ..models import AccountRegistration
import json
import logging
import time

logger = logging.getLogger(__name__)

@login_required
def get_face_embeddings_api(request):
    """API endpoint to get all face embeddings for the live feed"""
    try:
        # Initialize face matcher to get embeddings
        matcher = FaceMatcher(use_gpu=True)
        
        # Reload embeddings to ensure we have the latest ones
        matcher.load_embeddings()
        
        # Get all users with embeddings
        embeddings_data = []
        
        if hasattr(matcher, 'embeddings') and matcher.embeddings:
            for user_id, embedding_data in matcher.embeddings.items():
                try:
                    # Get user information
                    user = AccountRegistration.objects.filter(id_number=user_id).first()
                    if user:
                        embeddings_data.append({
                            'id_number': user_id,
                            'first_name': user.first_name,
                            'last_name': user.last_name,
                            'full_name': f"{user.first_name} {user.last_name}",
                            'department': user.department,
                            'privilege': user.privilege,
                            'status': user.status,
                            # Don't send actual embedding data for security/performance
                            'has_embedding': True
                        })
                except Exception as e:
                    logger.warning(f"Error processing embedding for user {user_id}: {e}")
                    continue
        
        return JsonResponse({
            'success': True,
            'embeddings': embeddings_data,
            'count': len(embeddings_data),
            'message': f'Successfully loaded {len(embeddings_data)} face embeddings'
        })
        
    except Exception as e:
        logger.error(f"Error getting face embeddings: {e}")
        return JsonResponse({
            'success': False,
            'embeddings': [],
            'count': 0,
            'error': str(e),
            'message': 'Failed to load face embeddings'
        }, status=500)

@login_required 
def get_camera_status_api(request):
    """API endpoint to get current camera status and face detection info"""
    try:
        from .video_feed_view import cameras, display_states
        
        camera_status = {}
        
        for camera_id in cameras:
            status_info = {
                'id': camera_id,
                'name': f'Camera {camera_id}',
                'is_active': cameras[camera_id] is not None,
                'face_count': 0,
                'detected_faces': [],
                'status': 'unknown'
            }
            
            if camera_id in display_states:
                state = display_states[camera_id]
                status_info.update({
                    'face_count': state.get('face_count', 0),
                    'last_update': state.get('last_update', 0),
                    'status': 'active' if cameras[camera_id] is not None else 'inactive'
                })
                
                # Get face detection results
                face_locations = state.get('face_locations', [])
                face_matches = state.get('face_matches', [])
                
                detected_faces = []
                for i, location in enumerate(face_locations):
                    face_info = {
                        'location': location,
                        'match_id': None,
                        'confidence': 0,
                        'user_info': None
                    }
                    
                    if i < len(face_matches) and face_matches[i]:
                        match = face_matches[i]
                        if match.get('match_id'):
                            face_info.update({
                                'match_id': match['match_id'],
                                'confidence': match.get('confidence', 0),
                                'user_info': {
                                    'first_name': match['user_info'].first_name if match.get('user_info') else '',
                                    'last_name': match['user_info'].last_name if match.get('user_info') else '',
                                    'department': match['user_info'].department if match.get('user_info') else '',
                                    'privilege': match['user_info'].privilege if match.get('user_info') else ''
                                } if match.get('user_info') else None
                            })
                    
                    detected_faces.append(face_info)
                
                status_info['detected_faces'] = detected_faces
            
            camera_status[camera_id] = status_info
        
        return JsonResponse({
            'success': True,
            'cameras': camera_status,
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error getting camera status: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'cameras': {}
        }, status=500)

@csrf_exempt
@login_required
def refresh_face_embeddings_api(request):
    """API endpoint to refresh face embeddings (useful after new enrollment)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        from .video_feed_view import matcher
        
        # Reload embeddings from database
        matcher.load_embeddings()
        
        # Count loaded embeddings
        embedding_count = len(matcher.embeddings) if hasattr(matcher, 'embeddings') and matcher.embeddings else 0
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully refreshed {embedding_count} face embeddings',
            'count': embedding_count
        })
        
    except Exception as e:
        logger.error(f"Error refreshing face embeddings: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': 'Failed to refresh face embeddings'
        }, status=500)


@login_required
def verify_face_embeddings_api(request):
    """API endpoint to verify face embeddings after enrollment"""
    try:
        from ..models import FacesEmbeddings
        from .enhanced_video_feed import enhanced_camera_manager
        
        # Get database embeddings count
        db_embeddings = FacesEmbeddings.objects.all()
        db_count = db_embeddings.count()
        
        # Get loaded embeddings count from enhanced camera manager
        matcher = enhanced_camera_manager.matcher
        loaded_count = len(matcher.embeddings) if hasattr(matcher, 'embeddings') and matcher.embeddings else 0
        
        # Get detailed embedding info
        embedding_details = []
        for embedding_record in db_embeddings:
            user_info = {
                'id_number': embedding_record.id_number.id_number,
                'first_name': embedding_record.id_number.first_name,
                'last_name': embedding_record.id_number.last_name,
                'created_at': embedding_record.created_at.isoformat(),
                'has_front': bool(embedding_record.front_embedding),
                'has_left': bool(embedding_record.left_embedding),
                'has_right': bool(embedding_record.right_embedding),
                'loaded_in_memory': embedding_record.id_number.id_number in matcher.embeddings if matcher.embeddings else False
            }
            embedding_details.append(user_info)
        
        return JsonResponse({
            'success': True,
            'database_count': db_count,
            'loaded_count': loaded_count,
            'embeddings_synced': db_count == loaded_count,
            'embedding_details': embedding_details,
            'message': f'Database has {db_count} embeddings, {loaded_count} loaded in memory'
        })
        
    except Exception as e:
        logger.error(f"Error verifying face embeddings: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': 'Failed to verify face embeddings'
        }, status=500)