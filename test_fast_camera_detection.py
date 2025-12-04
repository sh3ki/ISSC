"""
Test fast camera detection without opening cameras
"""

import subprocess
import json
import time

def fast_camera_detection():
    """Get camera names WITHOUT opening them - FAST!"""
    print("=" * 60)
    print("FAST CAMERA DETECTION (No Camera Opening)")
    print("=" * 60)
    
    start_time = time.time()
    
    powershell_command = """
    Get-PnpDevice -Class Camera,Image | 
    Where-Object {$_.Status -eq 'OK'} | 
    Select-Object FriendlyName, InstanceId | 
    ConvertTo-Json
    """
    
    print("\n📡 Querying Windows registry for cameras...")
    result = subprocess.run(
        ["powershell", "-Command", powershell_command],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    elapsed = time.time() - start_time
    
    if result.returncode == 0 and result.stdout.strip():
        devices = json.loads(result.stdout)
        
        if isinstance(devices, dict):
            devices = [devices]
        
        print(f"\n✅ Found {len(devices)} camera(s) in {elapsed:.3f} seconds:\n")
        
        camera_info = []
        for idx, device in enumerate(devices):
            friendly_name = device.get('FriendlyName', f'Camera {idx}')
            print(f"   [{idx}] {friendly_name}")
            camera_info.append({
                'id': idx,
                'name': friendly_name,
                'status': 'Available'
            })
        
        print(f"\n⚡ Detection took: {elapsed:.3f} seconds")
        print("✅ NO cameras were opened or turned on!")
        
        return camera_info
    else:
        print("❌ No cameras found")
        return []

if __name__ == "__main__":
    cameras = fast_camera_detection()
    
    print("\n" + "=" * 60)
    print("RESULT FOR DROPDOWN")
    print("=" * 60)
    for cam in cameras:
        print(f"  Option: {cam['name']} (ID: {cam['id']})")
    
    print("\n" + "=" * 60)
    print("✅ FAST & NO CAMERA FLICKER!")
    print("=" * 60)
