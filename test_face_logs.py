import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'issc.settings')
django.setup()

from main.models import FaceLogs
from django.utils import timezone
import datetime

# Check recent logs
threshold = timezone.now() - datetime.timedelta(hours=1)
recent = FaceLogs.objects.filter(created_at__gte=threshold).order_by('-created_at')[:10]

print(f"\n✅ Recent Face Logs (last hour): {recent.count()} entries\n")
print("-" * 80)

if recent.count() == 0:
    print("❌ NO RECENT LOGS FOUND!")
    print("\nChecking all logs from today:")
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_logs = FaceLogs.objects.filter(created_at__gte=today_start).order_by('-created_at')[:10]
    print(f"Found {today_logs.count()} logs today")
    for log in today_logs:
        print(f"  {log.id_number.id_number} - {log.id_number.first_name} {log.id_number.last_name} - {log.created_at}")
else:
    for log in recent:
        print(f"{log.id_number.id_number:12} | {log.id_number.first_name} {log.id_number.last_name:20} | {log.created_at}")

print("-" * 80)

# Test creating a new log
print("\n🧪 Testing log creation...")
from main.models import AccountRegistration

try:
    admin = AccountRegistration.objects.get(id_number='ADMIN001')
    
    # Check for recent duplicate
    two_sec_ago = timezone.now() - datetime.timedelta(seconds=2)
    duplicate = FaceLogs.objects.filter(id_number=admin, created_at__gte=two_sec_ago).first()
    
    if duplicate:
        print(f"⏳ Duplicate found within 2 seconds - cooldown active")
    else:
        new_log = FaceLogs.objects.create(
            id_number=admin,
            first_name=admin.first_name,
            middle_name=admin.middle_name or '',
            last_name=admin.last_name
        )
        print(f"✅ New log created: {new_log.id} - {admin.first_name} {admin.last_name} at {new_log.created_at}")
        
except Exception as e:
    print(f"❌ Error: {e}")
