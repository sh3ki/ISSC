#!/bin/bash
# Quick Email Configuration Fix for Production Server

echo "=========================================="
echo "ISSC Email Configuration Fix"
echo "=========================================="
echo ""

# Production .env file location
ENV_FILE="/var/www/issc/issc/issc/.env"

echo "Updating .env file with complete email configuration..."

# Update or add email configuration
cat > "$ENV_FILE" << 'EOF'
# Django Settings
SECRET_KEY='django-insecure-prod-key-change-in-production-2026'
DEBUG=False
ALLOWED_HOSTS=issc.study,www.issc.study,72.62.66.193

# Database Configuration - Production
DB_NAME=issc
DB_USER=issc_user
DB_PASSWORD=Issc@2024
DB_HOST=127.0.0.1
DB_PORT=3306

# Email Configuration (Gmail) - SMTP Settings
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=vinceerickquiozon14@gmail.com
EMAIL_HOST_PASSWORD=viqbpwklhlergez
DEFAULT_FROM_EMAIL=vinceerickquiozon14@gmail.com

# PhilSMS Configuration
PHILSMS_API_BASE=https://dashboard.philsms.com/api/v3
PHILSMS_API_TOKEN=377|DT0C9GeHCgLXdNt5oxjajd3QqdLlKcqMHv5KLZcE3b45ab96
PHILSMS_SENDER_ID=PhilSMS
PHILSMS_RECIPIENT=09945349194
PHILSMS_COOLDOWN_SECONDS=900
EOF

# Set proper permissions
chmod 640 "$ENV_FILE"
chown www-data:www-data "$ENV_FILE"

echo "✓ Email configuration updated in .env"
echo ""
echo "Email Settings:"
echo "  - Backend: django.core.mail.backends.smtp.EmailBackend"
echo "  - Host: smtp.gmail.com"
echo "  - Port: 587"
echo "  - TLS: Enabled"
echo "  - User: vinceerickquiozon14@gmail.com"
echo "  - Password: ****************** (configured)"
echo ""

echo "Restarting Gunicorn..."
systemctl restart gunicorn
sleep 2

echo ""
echo "Checking Gunicorn status..."
systemctl status gunicorn --no-pager | head -n 10
echo ""

echo "Testing email configuration..."
echo "Run this command to send a test email:"
echo "  cd /root/ISSC && python test_email.py"
echo ""
echo "Done! Email should now work on production server."
