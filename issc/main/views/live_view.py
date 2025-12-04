from django.http import HttpResponse
from django.template import loader
from django.shortcuts import render, redirect, get_object_or_404

from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required

from django.core.files.storage import FileSystemStorage
from django.core.paginator import Paginator

from ..models import AccountRegistration, IncidentReport, VehicleRegistration

from .utils import paginate


@login_required(login_url='/login/')
def live_feed(request):

    return StreamingHttpResponse(recognizer.generate_frames(), content_type="multipart/x-mixed-replace; boundary=frame")
    
    user = AccountRegistration.objects.filter(username=request.user).values()
    template = loader.get_template('live-feed/live-feed.html')
    context = {
        'user_role': user[0]['privilege'],
        'user_data':user[0]

    }
    return HttpResponse(template.render(context, request))