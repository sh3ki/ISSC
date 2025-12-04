import sys
import os
# Add the issc directory to the path
sys.path.append('./issc')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'issc.settings')

import django
django.setup()

print("🔥 MANUAL RAPOO CAMERA DETECTION TEST 🔥")
print("="*50)

from main.views.video_feed_view import detect_cameras

print("Calling detect_cameras() directly...")
cameras = detect_cameras()
print(f"Result: {cameras}")