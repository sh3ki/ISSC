from django.apps import AppConfig

class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'
    
    def ready(self):
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