#!/usr/bin/env python3
"""
Quick test to check what cameras are available at different physical indices
"""
import cv2
import time

def test_camera_index(index):
    """Test if a camera exists at the given index"""
    print(f"\n🔍 Testing camera at index {index}...")
    
    try:
        # Try multiple backends
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, 0]
        
        for backend_name, backend in [("DirectShow", cv2.CAP_DSHOW), ("Media Foundation", cv2.CAP_MSMF), ("Default", 0)]:
            print(f"  🔧 Trying {backend_name} backend...")
            
            cap = cv2.VideoCapture(index, backend)
            
            if cap.isOpened():
                print(f"    ✅ Camera opened with {backend_name}")
                
                # Try to read a frame
                time.sleep(0.5)  # Give camera time to initialize
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    h, w = frame.shape[:2]
                    print(f"    ✅ Successfully read frame: {w}x{h}")
                    cap.release()
                    return True
                else:
                    print(f"    ❌ Could not read frame")
                
                cap.release()
            else:
                print(f"    ❌ Could not open camera with {backend_name}")
                
    except Exception as e:
        print(f"    ❌ Error testing index {index}: {e}")
    
    return False

def main():
    print("🎥 Camera Detection Test")
    print("========================")
    
    found_cameras = []
    
    # Test indices 0-5
    for i in range(6):
        if test_camera_index(i):
            found_cameras.append(i)
    
    print(f"\n📊 Summary:")
    print(f"Found cameras at indices: {found_cameras}")
    
    if 2 in found_cameras:
        print("✅ Camera found at index 2 (should be Rapoo)")
    else:
        print("❌ No camera found at index 2")
        
    if 1 in found_cameras:
        print("✅ Camera found at index 1 (should be Acer HD)")
    else:
        print("❌ No camera found at index 1")

if __name__ == "__main__":
    main()