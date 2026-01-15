#!/usr/bin/env python
"""
Test Email Sending Script for ISSC Production Server
Run this script to verify that Gmail SMTP is working correctly.
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, '/var/www/issc/issc')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'issc.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

def test_email():
    """Send a test email to verify SMTP configuration"""
    
    print("=" * 60)
    print("ISSC Email Configuration Test")
    print("=" * 60)
    print()
    
    # Display current email settings
    print("Current Email Settings:")
    print(f"  EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"  EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"  EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"  EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"  EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"  EMAIL_HOST_PASSWORD: {'*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 'NOT SET'}")
    print(f"  DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print()
    
    # Test email details
    test_recipient = input("Enter recipient email address (or press Enter for default): ").strip()
    if not test_recipient:
        test_recipient = settings.EMAIL_HOST_USER
    
    subject = "ISSC Production Server - Email Test"
    message = """
    This is a test email from the ISSC Production Server.
    
    If you receive this email, it means the Gmail SMTP configuration is working correctly!
    
    Server Details:
    - Time: {}
    - Host: issc.study
    - Environment: Production
    
    Best regards,
    ISSC System
    """.format(django.utils.timezone.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    print(f"Sending test email to: {test_recipient}")
    print("Please wait...")
    print()
    
    try:
        # Send the email
        result = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[test_recipient],
            fail_silently=False,
        )
        
        if result == 1:
            print("✅ SUCCESS! Test email sent successfully!")
            print(f"   Check inbox for: {test_recipient}")
            print()
            print("Gmail SMTP is configured correctly and working on production server!")
        else:
            print("⚠️  Email function returned 0. Check configuration.")
            
    except Exception as e:
        print("❌ FAILED! Error sending email:")
        print(f"   {type(e).__name__}: {str(e)}")
        print()
        print("Troubleshooting tips:")
        print("1. Verify Gmail App Password is correct (16 characters, no spaces)")
        print("2. Check that 'Less secure app access' is enabled if using regular password")
        print("3. Verify .env file has correct EMAIL_HOST_PASSWORD")
        print("4. Check firewall allows outbound SMTP traffic on port 587")
        print("5. Ensure the Gmail account can send emails")
        return False
    
    print()
    print("=" * 60)
    return True

if __name__ == "__main__":
    test_email()
