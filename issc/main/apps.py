from django.apps import AppConfig
import os
import sys

class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'
    
    def ready(self):
        if os.environ.get('ISSC_DISABLE_GPU_INIT') == '1' or 'test' in sys.argv:
            print("Skipping GPU support initialization for tests/disabled mode.")
            return

        # Initialize GPU support when Django starts
        print("Initializing GPU support...")
        try:
            from .computer_vision.config import setup_gpu
            gpu_info = setup_gpu()
            print(f"GPU initialization complete: {gpu_info}")
            
            # Set device preference for face recognition
            device = 'cuda' if gpu_info.get('pytorch', False) else 'cpu'
            print(f"Face recognition will use device: {device}")
            
        except Exception as e:
            print(f"GPU initialization error: {e}")
            print("Continuing with CPU processing...")