from django.http import HttpResponse
from django.urls import path

from .views.incident_view import incident_forms


def _ok(_request, *args, **kwargs):
    return HttpResponse('ok')


urlpatterns = [
    path('incidents/forms', incident_forms, name='incident_forms'),
    path('incidents/<int:id>/', _ok, name='incident_details'),
    path('dashboard/', _ok, name='dashboard'),
]
