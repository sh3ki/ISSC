"""
Diagnostic script to check face embeddings in the database
Run this to verify embeddings are stored correctly
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.join(os.path.dirname(__file__), 'issc'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'issc.settings')
django.setup()

from main.models import FacesEmbeddings, AccountRegistration
import json

print("=" * 80)
print("🔍 FACE EMBEDDINGS DATABASE DIAGNOSTIC")
print("=" * 80)

# Get all face embeddings
embeddings = FacesEmbeddings.objects.all()
print(f"\n📊 Total face embedding records: {embeddings.count()}")

if embeddings.count() == 0:
    print("❌ No face embeddings found in database!")
    print("   Please enroll at least one face first.")
    sys.exit(0)

print("\n" + "=" * 80)

for idx, emb in enumerate(embeddings, 1):
    print(f"\n📋 Record #{idx}")
    print("-" * 80)
    
    # Get ID number
    try:
        id_num = emb.id_number.id_number if hasattr(emb.id_number, 'id_number') else str(emb.id_number)
        print(f"ID Number: {id_num}")
    except Exception as e:
        print(f"❌ Error getting ID number: {e}")
        id_num = "UNKNOWN"
    
    # Get account info
    try:
        account = AccountRegistration.objects.filter(id_number=id_num).first()
        if account:
            print(f"Name: {account.first_name} {account.last_name}")
            print(f"Email: {account.email}")
            print(f"Department: {account.department}")
            print(f"Privilege: {account.privilege}")
        else:
            print("⚠️ No account found for this ID")
    except Exception as e:
        print(f"❌ Error getting account info: {e}")
    
    # Check each embedding type
    print("\n🎭 Embeddings:")
    
    for emb_type in ['front_embedding', 'left_embedding', 'right_embedding']:
        try:
            emb_data = getattr(emb, emb_type)
            
            # Analyze the data type and content
            data_type = type(emb_data).__name__
            print(f"\n   {emb_type}:")
            print(f"      Type: {data_type}")
            
            if isinstance(emb_data, str):
                # Try to parse as JSON
                try:
                    parsed = json.loads(emb_data)
                    if isinstance(parsed, list):
                        print(f"      Status: ✅ Valid JSON list")
                        print(f"      Length: {len(parsed)} values")
                        if len(parsed) > 0:
                            print(f"      First 3 values: {parsed[:3]}")
                            print(f"      Last 3 values: {parsed[-3:]}")
                    else:
                        print(f"      Status: ⚠️ JSON but not a list")
                except json.JSONDecodeError:
                    print(f"      Status: ❌ Invalid JSON")
                    print(f"      Content preview: {str(emb_data)[:100]}")
            
            elif isinstance(emb_data, list):
                print(f"      Status: ✅ Python list")
                print(f"      Length: {len(emb_data)} values")
                if len(emb_data) > 0:
                    print(f"      First 3 values: {emb_data[:3]}")
                    print(f"      Last 3 values: {emb_data[-3:]}")
            
            elif isinstance(emb_data, dict):
                if len(emb_data) == 0:
                    print(f"      Status: ⚠️ Empty dict (no data captured)")
                else:
                    print(f"      Status: ⚠️ Dict with {len(emb_data)} keys")
                    print(f"      Keys: {list(emb_data.keys())}")
            
            else:
                print(f"      Status: ⚠️ Unexpected type")
                print(f"      Content: {emb_data}")
        
        except Exception as e:
            print(f"   ❌ Error checking {emb_type}: {e}")
    
    print(f"\n   Created: {emb.created_at}")
    print(f"   Updated: {emb.updated_at}")

print("\n" + "=" * 80)
print("✅ DIAGNOSTIC COMPLETE")
print("=" * 80)
print("\n💡 WHAT TO LOOK FOR:")
print("   - Each embedding should be a list with 512 values (FaceNet embedding size)")
print("   - If you see empty dicts {}, that angle wasn't captured during enrollment")
print("   - All values should be floating point numbers")
print("   - If front_embedding is valid, face recognition should work")
print("=" * 80)
