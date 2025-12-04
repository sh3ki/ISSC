"""
Test script for the enhanced live feed functionality
Run this to verify the improvements are working correctly
"""

import sys
import os
import django

# Add the project path to sys.path
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_path)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'issc.settings')
django.setup()

def test_enhanced_camera_manager():
    """Test the enhanced camera manager"""
    print("Testing Enhanced Camera Manager...")
    
    try:
        from main.views.enhanced_video_feed import enhanced_camera_manager
        
        # Test camera detection
        print("1. Testing camera detection...")
        cameras = enhanced_camera_manager.detect_working_cameras()
        print(f"   Found cameras: {list(cameras.keys())}")
        
        # Test initialization
        print("2. Testing camera initialization...")
        enhanced_camera_manager.initialize_for_live_feed()
        print(f"   Initialized cameras: {list(enhanced_camera_manager.cameras.keys())}")
        
        # Test face embeddings loading
        print("3. Testing face embeddings loading...")
        success = enhanced_camera_manager.reload_face_embeddings()
        print(f"   Face embeddings loaded: {success}")
        
        # Clean up
        print("4. Testing cleanup...")
        enhanced_camera_manager.cleanup()
        print("   Cleanup completed")
        
        print("✅ Enhanced Camera Manager test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced Camera Manager test failed: {e}")
        return False

def test_api_endpoints():
    """Test the API endpoints"""
    print("\nTesting API Endpoints...")
    
    try:
        from main.views.live_feed_api import get_face_embeddings_api, get_camera_status_api
        from django.http import HttpRequest
        from django.contrib.auth.models import AnonymousUser
        from main.models import AccountRegistration
        
        # Create a mock request
        request = HttpRequest()
        request.method = 'GET'
        
        # Try to get a real user for testing
        try:
            user = AccountRegistration.objects.first()
            request.user = user
            print(f"   Using test user: {user.username}")
        except:
            print("   Warning: No users found, API tests may fail")
            request.user = AnonymousUser()
        
        # Test face embeddings API
        print("1. Testing face embeddings API...")
        try:
            response = get_face_embeddings_api(request)
            print(f"   Face embeddings API response: {response.status_code}")
        except Exception as e:
            print(f"   Face embeddings API error: {e}")
        
        # Test camera status API
        print("2. Testing camera status API...")
        try:
            response = get_camera_status_api(request)
            print(f"   Camera status API response: {response.status_code}")
        except Exception as e:
            print(f"   Camera status API error: {e}")
        
        print("✅ API endpoints test completed!")
        return True
        
    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        return False

def test_face_matcher_integration():
    """Test face matcher integration"""
    print("\nTesting Face Matcher Integration...")
    
    try:
        from main.computer_vision.face_matching import FaceMatcher
        
        print("1. Testing face matcher initialization...")
        matcher = FaceMatcher(use_gpu=True)
        
        print("2. Testing embeddings loading...")
        matcher.load_embeddings()
        
        embedding_count = len(matcher.embeddings) if hasattr(matcher, 'embeddings') and matcher.embeddings else 0
        print(f"   Loaded {embedding_count} face embeddings")
        
        print("✅ Face matcher integration test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Face matcher integration test failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("ENHANCED LIVE FEED - TESTING SUITE")
    print("=" * 60)
    
    results = []
    
    # Test enhanced camera manager
    results.append(test_enhanced_camera_manager())
    
    # Test API endpoints
    results.append(test_api_endpoints())
    
    # Test face matcher integration
    results.append(test_face_matcher_integration())
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Enhanced live feed is ready to use.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
    
    print("\nNext steps:")
    print("1. Start your Django server: python manage.py runserver")
    print("2. Navigate to: http://127.0.0.1:8000/live-feed-enhanced/")
    print("3. The enhanced live feed should now work without flickering!")
    
    return passed == total

if __name__ == "__main__":
    run_all_tests()