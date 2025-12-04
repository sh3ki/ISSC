"""
Test to identify which OpenCV camera index corresponds to which physical camera
"""

import cv2
import subprocess
import json

def get_powershell_cameras():
    """Get camera names from PowerShell"""
    powershell_command = """
    Get-PnpDevice -Class Camera,Image | 
    Where-Object {$_.Status -eq 'OK'} | 
    Select-Object FriendlyName, InstanceId | 
    ConvertTo-Json
    """
    
    result = subprocess.run(
        ["powershell", "-Command", powershell_command],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    if result.returncode == 0 and result.stdout.strip():
        devices = json.loads(result.stdout)
        if isinstance(devices, dict):
            devices = [devices]
        return {idx: dev['FriendlyName'] for idx, dev in enumerate(devices)}
    return {}

def test_opencv_cameras():
    """Test which OpenCV indices work and capture a frame to identify"""
    print("=" * 60)
    print("TESTING OPENCV CAMERA INDICES")
    print("=" * 60)
    
    working_cameras = {}
    
    for i in range(5):
        print(f"\n🎥 Testing OpenCV Camera {i}...")
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                print(f"   ✅ Camera {i} WORKS! Resolution: {w}x{h}")
                
                # Save a test frame
                filename = f"camera_{i}_test.jpg"
                cv2.imwrite(filename, frame)
                print(f"   📸 Saved test image: {filename}")
                print(f"   👉 CHECK THIS IMAGE to identify which camera this is!")
                
                working_cameras[i] = True
            else:
                print(f"   ⚠️ Camera {i} opened but can't read")
            cap.release()
        else:
            print(f"   ❌ Camera {i} not available")
    
    return working_cameras

if __name__ == "__main__":
    # Get PowerShell camera names
    print("=" * 60)
    print("POWERSHELL CAMERA NAMES")
    print("=" * 60)
    ps_cameras = get_powershell_cameras()
    for idx, name in ps_cameras.items():
        print(f"PowerShell Index {idx}: {name}")
    
    # Test OpenCV cameras
    opencv_cameras = test_opencv_cameras()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("\nPowerShell cameras:")
    for idx, name in ps_cameras.items():
        print(f"  [{idx}] {name}")
    
    print("\nOpenCV working cameras:")
    for idx in opencv_cameras.keys():
        print(f"  OpenCV Camera {idx} - Check image: camera_{idx}_test.jpg")
    
    print("\n👉 INSTRUCTIONS:")
    print("1. Look at the generated camera_X_test.jpg files")
    print("2. Identify which is ACER and which is Rapoo")
    print("3. This will tell us the correct mapping!")
    print("=" * 60)
