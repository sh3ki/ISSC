#!/bin/bash
# Quick fix for production .env database configuration

echo "Creating production .env file with correct database credentials..."

# Production .env file location
ENV_FILE="/var/www/issc/issc/issc/.env"

# Create the .env file
cat > "$ENV_FILE" << 'EOF'
# Django Settings
SECRET_KEY='your-production-secret-key-change-this'
DEBUG=False
ALLOWED_HOSTS=issc.study,www.issc.study,72.62.66.193

# Database Configuration - Production
DB_NAME=issc
DB_USER=issc_user
DB_PASSWORD=Issc@2024
DB_HOST=127.0.0.1
DB_PORT=3306

# Email Configuration (Gmail)
EMAIL_HOST_USER=vinceerickquiozon14@gmail.com
EMAIL_HOST_PASSWORD=viqbpwklhlergez

# PhilSMS Configuration
PHILSMS_API_BASE=https://dashboard.philsms.com/api/v3
PHILSMS_API_TOKEN=377|DT0C9GeHCgLXdNt5oxjajd3QqdLlKcqMHv5KLZcE3b45ab96
PHILSMS_SENDER_ID=PhilSMS
PHILSMS_RECIPIENT=09945349194
PHILSMS_COOLDOWN_SECONDS=900
EOF

# Set secure permissions
chmod 600 "$ENV_FILE"
chown www-data:www-data "$ENV_FILE"

echo "✓ .env file created with:"
echo "  - Database: issc"
echo "  - User: issc_user"
echo "  - Password: Issc@2024"
echo ""
echo "Restarting Gunicorn..."
systemctl restart gunicorn
sleep 2
systemctl status gunicorn --no-pager

echo ""
echo "Done! The database error should be fixed."
