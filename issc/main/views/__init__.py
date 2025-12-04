from .auth_view import login
from .auth_view import logout

from .dashboard_view import base

from .incident_view import incident
from .incident_view import incident_forms
from .incident_view import incident_details

from .vehicle_view import vehicles
from .vehicle_view import vehicle_forms
from .vehicle_view import vehicle_details

from .live_view import live_feed

from .about_view import about

from .face_enrollment_view import face_enrollment
from .unauthorized_faces_view import unauthorized_faces_archive

# Import simplified live feed module
from . import live_feed_simple
