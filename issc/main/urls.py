from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import (
        auth_view, 
        dashboard_view, 
        incident_view, 
        vehicle_view, 
        about_view, 
        face_enrollment_view, 
        video_feed_view,
        utils,
        live_feed_api,
        enhanced_video_feed,
        lightning_camera_system,
        simple_lightning_camera,
        ultra_fast_camera,
        live_feed_simple
    ) 
urlpatterns = [

    path("login/", auth_view.login, name='login'),
    path("logout/", auth_view.logout, name="logout"),
    path("signup/", auth_view.signup, name='signup'),
    path("signup-forms/", auth_view.signup_forms, name='signup-forms'),
    path("import/",auth_view.import_data, name='import-forms'),
    path('get-user/', auth_view.getUser, name='get_user'),

    path("account/password-reset/", auth_view.CustomPasswordResetView.as_view(), name="password_reset"),
    # path("account/password-reset/done/", auth_view.CustomPasswordResetDoneView.as_view(), name="password_reset_done"),
    path('account/password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/acc_reset_done.html'), name='password_reset_done'),

    path("account/password-reset-confirm/<uidb64>/<token>/", auth_view.CustomPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("account/password-reset-complete/", auth_view.CustomPasswordResetCompleteView.as_view(), name="password_reset_complete"),



    path("", dashboard_view.base, name="dashboard"),
    path("dashboard/", dashboard_view.base, name="dashboard"),
    path("dashboard/print", dashboard_view.base_print, name="dashboard_print") ,



    path("incidents/", incident_view.incident, name="incidents"),
    path("incidents/forms", incident_view.incident_forms, name="incident_forms"),
    path('incidents/<int:id>/', incident_view.incident_details, name='incident_details'),
    path('incidents/<int:id>/print', incident_view.incident_print, name='incident_print'),

    path("vehicles/", vehicle_view.vehicles, name="vehicles"),
    path("vehicles/forms", vehicle_view.vehicle_forms, name="vehicle_forms"),
    path('vehicles/<int:id>/', vehicle_view.vehicle_details, name='vehicle_details'),
    path('vehicles/<int:id>/print', vehicle_view.vehicle_print, name='vehicle_print'),


    # LIVE FEED - Simplified version (fresh start, no camera/face recognition backend)
    path('live-feed/', live_feed_simple.live_feed_simple, name='multiple_streams'),
    path('video-feed/<int:camera_id>/', live_feed_simple.video_feed_simple, name='video_feed'),
    path('api/available-cameras/', live_feed_simple.get_available_cameras_simple, name='get_available_cameras'),
    path('api/initialize-live-feed-camera/', live_feed_simple.initialize_live_feed_camera, name='initialize_live_feed_camera'),
    path('api/stop-live-feed/', live_feed_simple.stop_live_feed, name='stop_live_feed'),
    path('live-feed/archive', live_feed_simple.recording_archive_simple, name="recording_archive"),
    path('live-feed/face-logs', live_feed_simple.face_logs_simple, name='face_logs'),
    path('live-feed/unauthorized-faces', views.unauthorized_faces_archive, name='unauthorized_faces_archive'),
    
    # OLD LIVE FEED ROUTES (kept for reference, but not used)
    # path('video-feed/<int:camera_id>/', video_feed_view.video_feed, name='video_feed'),
    # path('live-feed/', video_feed_view.multiple_streams, name='multiple_streams'),
    path('live-feed/start-record', video_feed_view.start_record, name='start_record'),
    path('live-feed/stop-record', video_feed_view.stop_record, name='stop_record'),
    path('check_cams/', video_feed_view.check_cams, name='check_cams'),
    # path('api/available-cameras/', video_feed_view.get_available_cameras, name='get_available_cameras'),
    # path('live-feed/archive', video_feed_view.recording_archive, name="recording_archive"),
    path('live-feed/reset', video_feed_view.reset_recordings, name="reset_recordings"),
    path('api/convert-video/', video_feed_view.convert_video_for_preview, name="convert_video"),
    path('live-feed/status', video_feed_view.recording_status, name='recording_status'),
    # path('live-feed/face-logs', video_feed_view.face_logs, name='face_logs'),
    
    # Enhanced live feed (kept for reference)
    path('live-feed-enhanced/', enhanced_video_feed.enhanced_live_feed, name='enhanced_live_feed'),
    path('enhanced-video-feed/<int:camera_id>/', enhanced_video_feed.enhanced_video_feed, name='enhanced_video_feed'),
    
    # Lightning live feed (ultra-fast version)
    path('lightning-live-feed/', lightning_camera_system.lightning_live_feed, name='lightning_live_feed'),
    path('lightning-video-feed/<int:camera_id>/', lightning_camera_system.lightning_video_feed, name='lightning_video_feed'),
    
    # Simple Lightning (working version)
    path('simple-lightning/', simple_lightning_camera.simple_lightning_live_feed, name='simple_lightning_live_feed'),
    path('simple-lightning-video/<int:camera_id>/', simple_lightning_camera.simple_lightning_video_feed, name='simple_lightning_video_feed'),
    
    # ULTRA-FAST Lightning (SUB-2 second loading)
    path('ultra-fast-live-feed/', ultra_fast_camera.ultra_fast_live_feed, name='ultra_fast_live_feed'),
    path('ultra-fast-video/<int:camera_id>/', ultra_fast_camera.ultra_fast_video_feed, name='ultra_fast_video_feed'),
    
    # API endpoints for live feed
    path('api/face-embeddings/', live_feed_api.get_face_embeddings_api, name='get_face_embeddings_api'),
    path('api/camera-status/', live_feed_api.get_camera_status_api, name='get_camera_status_api'),
    path('api/refresh-embeddings/', live_feed_api.refresh_face_embeddings_api, name='refresh_face_embeddings_api'),
    path('api/verify-embeddings/', live_feed_api.verify_face_embeddings_api, name='verify_face_embeddings_api'),
    path('live-feed/start-record', video_feed_view.start_record, name='start_record'),
    path('live-feed/stop-record', video_feed_view.stop_record, name='stop_record'),
    path('check_cams/', video_feed_view.check_cams, name='check_cams'),
    path('api/available-cameras/', video_feed_view.get_available_cameras, name='get_available_cameras'),
    path('live-feed/archive', video_feed_view.recording_archive, name="recording_archive"),
    path('live-feed/reset', video_feed_view.reset_recordings, name="reset_recordings"),
    path('api/convert-video/', video_feed_view.convert_video_for_preview, name="convert_video"),
    path('live-feed/status', video_feed_view.recording_status, name='recording_status'),

    path('live-feed/face-logs', video_feed_view.face_logs, name='face_logs'),

    path("about/", about_view.about, name="about"),

    
    path("face-enrollment/enrollee", face_enrollment_view.enrollee_view, name="enrollee_view"),
    path("face-enrollment/<str:id_number>", face_enrollment_view.face_enrollment_view, name="face_enrollment"),
    path('face_feed/', face_enrollment_view.face_video_feed, name='face_feed'),
    path('face-enrollment/success', face_enrollment_view.success_page, name='success_page'),
    path('face-enrollment/error', face_enrollment_view.error_page, name='error_page'),


    path('api/face-status', video_feed_view.frame_status_view, name='face_status'),
    path('api/getUser/', utils.getUser, name='getUserInfo'),
]

