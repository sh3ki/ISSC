import os
import torch
try:
    import tensorflow as tf
except Exception:
    tf = None
import cv2

def setup_gpu():
    """Configure all libraries to use GPU optimally"""
    gpu_info = {
        "tensorflow": False,
        "pytorch": False, 
        "opencv_cuda": False
    }
    
    # Set environment variables
    os.environ['TF_FORCE_GPU_ALLOWED_GROWTH'] = 'true'
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Reduce TensorFlow logging verbosity
    os.environ['CUDA_LAUNCH_BLOCKING'] = '1'  # Add this line to debug CUDA errors
    
    # Configure TensorFlow (optional)
    if tf is not None and hasattr(tf, "config"):
        try:
            gpus = tf.config.list_physical_devices('GPU')
            if gpus:
                for gpu in gpus:
                    if hasattr(tf, "config") and hasattr(tf.config, "experimental") and hasattr(tf.config.experimental, "set_memory_growth"):
                        tf.config.experimental.set_memory_growth(gpu, True)
                gpu_info["tensorflow"] = True
                print(f"TensorFlow using GPU: {getattr(tf.test, 'gpu_device_name', lambda: 'unknown')()}")
            else:
                print("TensorFlow GPU not available; running on CPU")
        except Exception as e:
            print(f"TensorFlow GPU acceleration not available: {e}")
    else:
        print("TensorFlow not installed or missing GPU APIs; skipping TF GPU setup")
    
    # Configure PyTorch with more careful memory management
    try:
        if torch.cuda.is_available():
            # Use a more careful GPU configuration to avoid misaligned address errors
            torch.cuda.empty_cache()
            # Use default device but don't change default tensor type
            torch.cuda.set_device(0)
            gpu_info["pytorch"] = True
            print(f"PyTorch using GPU: {torch.cuda.get_device_name(0)}")
        else:
            print("PyTorch CUDA not available")
    except Exception as e:
        print(f"PyTorch GPU acceleration not available: {e}")
    
    # Configure OpenCV
    try:
        cv2.setUseOptimized(True)
        cuda_devices = cv2.cuda.getCudaEnabledDeviceCount()
        if cuda_devices > 0:
            cv2.cuda.setDevice(0)
            gpu_info["opencv_cuda"] = True
            print(f"OpenCV using CUDA with {cuda_devices} device(s)")
        else:
            print("OpenCV CUDA not available - standard OpenCV will be used")
    except Exception as e:
        print(f"OpenCV CUDA acceleration not available: {e}")
    
    print(f"GPU initialization complete: {gpu_info}")
    return gpu_info

# Initialize GPU configuration when module is imported
gpu_config = setup_gpu()