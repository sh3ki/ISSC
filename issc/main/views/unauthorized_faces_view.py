"""
Unauthorized Faces Archive View
Displays all unauthorized face detections with pagination
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.conf import settings
from django.http import FileResponse, Http404
import os
from ..models import AccountRegistration, UnauthorizedFaceDetection


@login_required(login_url='/login/')
def unauthorized_faces_archive(request):
    """
    Display all unauthorized face detections with images
    Paginated to 20 items per page
    """
    # Get user info
    user = AccountRegistration.objects.filter(username=request.user).values()
    
    # Get all unauthorized face detections, ordered by most recent first
    all_detections = UnauthorizedFaceDetection.objects.all().order_by('-detection_timestamp')
    
    # Normalize image paths for web URLs (convert backslashes to forward slashes)
    for detection in all_detections:
        detection.image_path = detection.image_path.replace('\\', '/')
    
    # Paginate: 20 items per page
    paginator = Paginator(all_detections, 20)
    page_number = request.GET.get('page')
    detections = paginator.get_page(page_number)
    
    context = {
        'user_role': user[0]['privilege'] if user else 'Unknown',
        'user_data': user[0] if user else None,
        'detections': detections,
        'total_count': all_detections.count(),
        'MEDIA_URL': settings.MEDIA_URL,  # Add MEDIA_URL to context
    }
    
    return render(request, 'unauthorized_faces/archive.html', context)


@login_required(login_url='/login/')
def unauthorized_face_image(request, detection_id):
    detection = get_object_or_404(UnauthorizedFaceDetection, detection_id=detection_id)
    relative_path = detection.image_path.replace('\\', '/')
    file_path = os.path.join(settings.MEDIA_ROOT, relative_path)

    if not os.path.exists(file_path):
        raise Http404('Image not found')

    return FileResponse(open(file_path, 'rb'), content_type='image/jpeg')
