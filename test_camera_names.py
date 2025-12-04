"""
Test script to detect and display actual camera names on Windows
"""

import subprocess
import json
import cv2

def get_windows_camera_names():
    """Get actual camera device names on Windows using WMI"""
    print("=" * 60)
    print("DETECTING CAMERA NAMES ON WINDOWS")
    print("=" * 60)
    
    camera_names = {}
    try:
        # Use PowerShell to get camera names via WMI
        powershell_command = """
        Get-PnpDevice -Class Camera | 
        Where-Object {$_.Status -eq 'OK'} | 
        Select-Object FriendlyName, InstanceId | 
        ConvertTo-Json
        """
        
        print("\n📡 Querying Windows for camera devices...")
        result = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout:
            devices = json.loads(result.stdout)
            
            # Handle single device (not a list)
            if isinstance(devices, dict):
                devices = [devices]
            
            print(f"\n✅ Found {len(devices)} camera device(s):\n")
            
            # Map camera names by index
            for idx, device in enumerate(devices):
                friendly_name = device.get('FriendlyName', f'Camera {idx}')
                camera_names[idx] = friendly_name
                print(f"   [{idx}] {friendly_name}")
        else:
            print("❌ No cameras found or PowerShell error")
            print(f"Error output: {result.stderr}")
        
    except Exception as e:
        print(f"⚠️ Error getting camera names: {e}")
    
    return camera_names


def test_camera_access():
    """Test actual camera access with OpenCV"""
    print("\n" + "=" * 60)
    print("TESTING CAMERA ACCESS WITH OpenCV")
    print("=" * 60)
    
    for i in range(5):
        print(f"\n🎥 Testing Camera {i}...")
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                print(f"   ✅ Camera {i} is WORKING! Resolution: {w}x{h}")
            else:
                print(f"   ⚠️ Camera {i} opened but can't read frames")
            cap.release()
        else:
            print(f"   ❌ Camera {i} not available")


if __name__ == "__main__":
    # Get camera names
    camera_names = get_windows_camera_names()
    
    # Test camera access
    test_camera_access()
    
    # Show mapping
    if camera_names:
        print("\n" + "=" * 60)
        print("CAMERA MAPPING")
        print("=" * 60)
        for idx, name in camera_names.items():
            print(f"Camera Index {idx} → {name}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
