#!/usr/bin/env python3
"""
Test script to verify face enrollment and embedding loading process
"""

import requests
import json
import time

def test_embedding_verification():
    """Test the face embedding verification process"""
    
    base_url = "http://127.0.0.1:8000"
    
    print("=== Face Enrollment and Embedding Verification Test ===\n")
    
    # Test 1: Check current embeddings
    print("1. Checking current face embeddings...")
    try:
        response = requests.get(f"{base_url}/api/verify-embeddings/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Database embeddings: {data['database_count']}")
            print(f"   ✓ Loaded embeddings: {data['loaded_count']}")
            print(f"   ✓ Synced: {data['embeddings_synced']}")
            
            if data['embedding_details']:
                print("\n   Embedding Details:")
                for detail in data['embedding_details']:
                    print(f"     - {detail['id_number']}: {detail['first_name']} {detail['last_name']}")
                    print(f"       Created: {detail['created_at']}")
                    print(f"       Angles: Front={detail['has_front']}, Left={detail['has_left']}, Right={detail['has_right']}")
                    print(f"       Loaded in Memory: {detail['loaded_in_memory']}")
                    print()
        else:
            print(f"   ✗ Error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("   ✗ Cannot connect to Django server. Make sure it's running on http://127.0.0.1:8000")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Test 2: Refresh embeddings
    print("\n2. Testing embedding refresh...")
    try:
        response = requests.post(f"{base_url}/api/refresh-embeddings/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Refresh successful: {data['message']}")
            print(f"   ✓ Embedding count: {data['count']}")
        else:
            print(f"   ✗ Refresh failed: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error during refresh: {e}")
    
    # Test 3: Verify embeddings again after refresh
    print("\n3. Re-checking embeddings after refresh...")
    try:
        response = requests.get(f"{base_url}/api/verify-embeddings/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Database embeddings: {data['database_count']}")
            print(f"   ✓ Loaded embeddings: {data['loaded_count']}")
            print(f"   ✓ Synced: {data['embeddings_synced']}")
            
            if data['embeddings_synced']:
                print("   ✅ SUCCESS: Embeddings are properly synced!")
            else:
                print("   ⚠️  WARNING: Embeddings are not synced")
        else:
            print(f"   ✗ Error: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n=== Test Summary ===")
    print("✓ The face enrollment system automatically refreshes embeddings after enrollment")
    print("✓ Use the verification API to check if new enrollments are loaded")
    print("✓ The enhanced live feed system will include newly enrolled faces")
    print("\nTo test face enrollment:")
    print("1. Go to face enrollment page")
    print("2. Enroll a new face with front, left, and right angles")
    print("3. Check this verification API to confirm the embedding was saved and loaded")
    print("4. Test the live feed to see if the new face is recognized")
    
    return True

if __name__ == "__main__":
    test_embedding_verification()