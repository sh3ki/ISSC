#!/usr/bin/env python3
"""
Test script to check camera loading functionality
"""
import requests
import time

def test_camera_endpoints():
    """Test the camera endpoints"""
    base_url = "http://127.0.0.1:8000"
    
    print("Testing Enhanced Live Feed Camera Loading...")
    print("=" * 50)
    
    # Test main page first
    try:
        print("1. Testing main enhanced live feed page...")
        response = requests.get(f"{base_url}/live-feed-enhanced/", timeout=10)
        print(f"   Live feed page status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Live feed page loaded successfully")
        else:
            print(f"   ❌ Live feed page failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error accessing live feed page: {e}")
    
    # Test camera endpoints
    camera_ids = [0, 1, 2]
    
    for camera_id in camera_ids:
        try:
            print(f"\n2. Testing camera {camera_id} endpoint...")
            response = requests.head(f"{base_url}/enhanced-video-feed/{camera_id}/", timeout=5)
            print(f"   Camera {camera_id} status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ Camera {camera_id} endpoint working")
                print(f"   Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            elif response.status_code == 404:
                print(f"   ⚠️  Camera {camera_id} not found (expected if no physical camera)")
            elif response.status_code == 503:
                print(f"   ⏳ Camera {camera_id} still initializing...")
            else:
                print(f"   ❌ Camera {camera_id} error: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"   ⏳ Camera {camera_id} timeout (still loading)")
        except Exception as e:
            print(f"   ❌ Error testing camera {camera_id}: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_camera_endpoints()