"""
Simple camera test to isolate the issue
"""
import cv2
import time

def test_cameras():
    print("🔍 Testing camera detection...")
    
    for camera_id in range(5):
        print(f"Testing camera {camera_id}...")
        try:
            cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    print(f"✅ Camera {camera_id} WORKS!")
                    cap.release()
                    return camera_id
                else:
                    print(f"❌ Camera {camera_id} no frame")
            else:
                print(f"❌ Camera {camera_id} cannot open")
            cap.release()
        except Exception as e:
            print(f"❌ Camera {camera_id} error: {e}")
        
        time.sleep(0.5)
    
    print("❌ No working cameras found")
    return None

if __name__ == "__main__":
    test_cameras()