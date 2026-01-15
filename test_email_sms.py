#!/usr/bin/env python3
"""
Test Email and SMS Functionality
Run this on the server to verify email and SMS are working
"""

import os
import sys
import django

# Add project directory to path
sys.path.insert(0, '/root/ISSC/issc')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'issc.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings
from main.utils.philsms import send_sms_sync_verbose

print("=" * 60)
print("ISSC Email & SMS Test Script")
print("=" * 60)
print()

# Test Email
print("📧 Testing Email Configuration...")
print("-" * 60)
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"EMAIL_HOST_PASSWORD: {'*' * 16 if settings.EMAIL_HOST_PASSWORD else 'NOT SET'}")
print()

try:
    print("Sending test email...")
    send_mail(
        subject='ISSC Test Email - Deployment Check',
        message='This is a test email from ISSC deployed on Ubuntu server. If you receive this, email is working correctly!',
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[settings.EMAIL_HOST_USER],  # Send to self for testing
        fail_silently=False,
    )
    print("✅ Email sent successfully!")
    print()
except Exception as e:
    print(f"❌ Email failed: {e}")
    print()

# Test SMS
print("📱 Testing PhilSMS Configuration...")
print("-" * 60)

# Get PhilSMS settings
try:
    from main.utils.philsms import PHILSMS_API_BASE, PHILSMS_API_TOKEN, PHILSMS_SENDER_ID, PHILSMS_DEFAULT_RECIPIENT
    
    print(f"PHILSMS_API_BASE: {PHILSMS_API_BASE}")
    print(f"PHILSMS_API_TOKEN: {PHILSMS_API_TOKEN[:20]}..." if PHILSMS_API_TOKEN else "NOT SET")
    print(f"PHILSMS_SENDER_ID: {PHILSMS_SENDER_ID}")
    print(f"PHILSMS_RECIPIENT: {PHILSMS_DEFAULT_RECIPIENT}")
    print()
    
    print("Sending test SMS...")
    success, status_code, response_text = send_sms_sync_verbose(
        to_number=PHILSMS_DEFAULT_RECIPIENT,
        message="ISSC Test SMS - Deployment Check. System is working!"
    )
    
    print(f"Status Code: {status_code}")
    print(f"Response: {response_text}")
    
    if success:
        print("✅ SMS sent successfully!")
    else:
        print("❌ SMS failed!")
        print("⚠️  Check:")
        print("   - PhilSMS API token is valid")
        print("   - PhilSMS account has credits")
        print("   - Recipient phone number is correct format")
    print()
    
except Exception as e:
    print(f"❌ SMS test failed: {e}")
    print()

print("=" * 60)
print("Test Complete!")
print("=" * 60)
print()
print("If tests failed, check:")
print("1. .env file has correct EMAIL_HOST_USER and EMAIL_HOST_PASSWORD")
print("2. Gmail app password is correct (16 characters, no spaces)")
print("3. PhilSMS API token is valid and account has credits")
print("4. Server can access external SMTP and API endpoints")
print("   - Check firewall: sudo ufw status")
print("   - Test connectivity: curl https://smtp.gmail.com")
print()
