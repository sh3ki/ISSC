# Complete Deployment Guide: ISSC Django System on Hostinger KVM2 VPS
## Ubuntu 24.04 + Namecheap Domain

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Initial VPS Setup](#initial-vps-setup)
3. [Domain Configuration](#domain-configuration)
4. [Server Security Configuration](#server-security-configuration)
5. [Install System Dependencies](#install-system-dependencies)
6. [MySQL Database Setup](#mysql-database-setup)
7. [Python Environment Setup](#python-environment-setup)
8. [Deploy Django Application](#deploy-django-application)
9. [Configure Nginx Web Server](#configure-nginx-web-server)
10. [SSL Certificate Setup](#ssl-certificate-setup)
11. [Configure Gunicorn Service](#configure-gunicorn-service)
12. [Final Configuration & Testing](#final-configuration--testing)
13. [Maintenance & Monitoring](#maintenance--monitoring)
14. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### What You Need:
- Hostinger KVM2 VPS with Ubuntu 24.04
- Namecheap domain name
- Root or sudo access to VPS
- SSH client (PuTTY for Windows, Terminal for Mac/Linux)
- Your project files ready

### Information to Gather:
- VPS IP address (from Hostinger panel)
- Domain name (from Namecheap)
- Root password (from Hostinger email)

---

## 1. Initial VPS Setup

### Step 1.1: Access Your VPS

**From Windows (using PuTTY):**
1. Download PuTTY from https://www.putty.org/
2. Open PuTTY
3. Enter your VPS IP address in "Host Name"
4. Port: 22
5. Click "Open"
6. Login as: `root`
7. Enter password from Hostinger

**From Mac/Linux (using Terminal):**
```bash
ssh root@YOUR_VPS_IP
# Enter password when prompted
```

### Step 1.2: Update System

```bash
# Update package lists
apt update

# Upgrade all packages
apt upgrade -y

# Install essential build tools
apt install -y build-essential software-properties-common
```

### Step 1.3: Create a New User (Security Best Practice)

```bash
# Create a new user (replace 'isscadmin' with your preferred username)
adduser isscadmin

# Add user to sudo group
usermod -aG sudo isscadmin

# Switch to new user
su - isscadmin
```

---

## 2. Domain Configuration

### Step 2.1: Configure DNS at Namecheap

1. **Login to Namecheap account**
2. **Go to Domain List** → Select your domain
3. **Click "Manage"**
4. **Navigate to "Advanced DNS"**
5. **Add/Modify these records:**

| Type | Host | Value | TTL |
|------|------|-------|-----|
| A Record | @ | YOUR_VPS_IP | Automatic |
| A Record | www | YOUR_VPS_IP | Automatic |

**Example:**
```
Type: A Record
Host: @
Value: 123.45.67.89  (your VPS IP)
TTL: Automatic

Type: A Record
Host: www
Value: 123.45.67.89  (your VPS IP)
TTL: Automatic
```

6. **Save all changes**
7. **Wait 5-30 minutes for DNS propagation**

### Step 2.2: Verify DNS Propagation

```bash
# Check if domain points to your VPS
ping yourdomain.com

# Or use nslookup
nslookup yourdomain.com
```

---

## 3. Server Security Configuration

### Step 3.1: Configure Firewall (UFW)

```bash
# Allow SSH (IMPORTANT - do this first, before enabling UFW!)
sudo ufw allow OpenSSH

# Allow HTTP (port 80)
sudo ufw allow 80/tcp

# Allow HTTPS (port 443)
sudo ufw allow 443/tcp

# Enable UFW firewall
sudo ufw enable

# Press 'y' when prompted to confirm

# Check firewall status
sudo ufw status
```

**Note:** We allow SSH first before enabling the firewall to prevent locking yourself out.

### Step 3.2: Configure SSH (Optional but Recommended)

```bash
# Edit SSH configuration
sudo nano /etc/ssh/sshd_config
```

**Find and modify these lines:**
```
PermitRootLogin no           # Disable root login
PasswordAuthentication yes   # Keep yes initially, change to no after setting up SSH keys
Port 22                      # Or change to custom port for extra security
```

**Save and restart SSH:**
```bash
# Save: Ctrl+O, Enter
# Exit: Ctrl+X

# Restart SSH service
sudo systemctl restart ssh
```

---

## 4. Install System Dependencies

### Step 4.1: Install Python 3.12 and Dependencies

```bash
# Install Python 3.12 and pip (default in Ubuntu 24.04)
sudo apt install -y python3.12 python3.12-venv python3-pip python3.12-dev python3-full

# Install MySQL client libraries
sudo apt install -y default-libmysqlclient-dev pkg-config

# Install GEOS library (required for shapely geospatial library)
sudo apt install -y libgeos-dev

# Install OpenCV dependencies (required for face recognition)
sudo apt install -y libgl1 libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev

# Install additional dependencies for DeepFace and image processing
sudo apt install -y libhdf5-dev libatlas-base-dev libjasper-dev libqtgui4 libqt4-test

# Install Nginx web server
sudo apt install -y nginx

# Install Git
sudo apt install -y git

# Install system libraries for Pillow
sudo apt install -y libjpeg-dev zlib1g-dev libtiff-dev libfreetype6-dev liblcms2-dev libwebp-dev
```

### Step 4.2: Verify Python Installation

```bash
python3.12 --version
# Should show: Python 3.12.x
```

---

## 5. MySQL Database Setup

### Step 5.1: Install MySQL Server

```bash
# Install MySQL Server
sudo apt install -y mysql-server

# Start MySQL service
sudo systemctl start mysql
sudo systemctl enable mysql
```

### Step 5.2: Secure MySQL Installation

```bash
# Run security script
sudo mysql_secure_installation
```

**Answer the prompts:**
- Validate Password Component: **Yes** (recommended)
- Password Validation Policy: **2** (STRONG)
- Set root password: **Choose a strong password**
- Remove anonymous users: **Yes**
- Disallow root login remotely: **Yes**
- Remove test database: **Yes**
- Reload privilege tables: **Yes**

### Step 5.3: Create Database and User

```bash
# Login to MySQL as root
sudo mysql -u root -p
# Enter the root password you just set
```

**Inside MySQL shell, run:**
```sql
-- Create database
CREATE DATABASE issc_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user (replace 'strong_password_here' with a strong password)
CREATE USER 'issc_user'@'localhost' IDENTIFIED BY 'strong_password_here';

-- Grant privileges
GRANT ALL PRIVILEGES ON issc_db.* TO 'issc_user'@'localhost';

-- Flush privileges
FLUSH PRIVILEGES;

-- Verify
SHOW DATABASES;

-- Exit MySQL
EXIT;
```

### Step 5.4: Test Database Connection

```bash
# Test login with new user
mysql -u issc_user -p
# Enter the password you created

# Inside MySQL:
SHOW DATABASES;
# You should see issc_db

EXIT;
```

---

## 6. Python Environment Setup

### Step 6.1: Create Project Directory

```bash
# Create directory for your application
sudo mkdir -p /var/www/issc
sudo chown -R $USER:$USER /var/www/issc
cd /var/www/issc
```

### Step 6.2: Create Virtual Environment

```bash
# Create virtual environment with Python 3.12
python3.12 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### Step 6.3: Install Python Dependencies

**You'll upload your requirements.txt file later, but here's how to install:**

```bash
# After uploading requirements.txt to /var/www/issc/
pip install -r requirements.txt

# Install additional production dependencies
pip install gunicorn mysqlclient python-dotenv
```

**Note:** If you encounter errors with `mysqlclient`, ensure you installed the dev packages in Step 4.1.

---

## 7. Deploy Django Application

### Step 7.1: Upload Your Project Files

**Option 1: Using Git (Recommended)**

```bash
# If your project is on GitHub
cd /var/www/issc
git clone https://github.com/yourusername/your-repo.git .

# Or if you have a private repo
git clone https://your-git-url.git .
```

**Option 2: Using SCP/SFTP (from your local machine)**

**From Windows (using WinSCP):**
1. Download WinSCP: https://winscp.net/
2. Connect to your VPS (IP, port 22, username, password)
3. Navigate to `/var/www/issc/`
4. Upload your entire project folder

**From Mac/Linux:**
```bash
# From your local machine
scp -r /path/to/ISSC-Django-main/* isscadmin@YOUR_VPS_IP:/var/www/issc/

# Example:
# scp -r C:\Users\USER\Downloads\ISSC-Django-main\* isscadmin@123.45.67.89:/var/www/issc/
```

### Step 7.2: Verify File Structure

```bash
cd /var/www/issc
ls -la

# You should see:
# - issc/ (Django project folder)
# - requirements.txt
# - venv/
# - etc.
```

### Step 7.3: Create Environment Variables File

```bash
cd /var/www/issc
nano .env
```

**Add these variables (customize values):**
```bash
# Django Settings
SECRET_KEY='your-very-long-random-secret-key-generate-new-one'
DEBUG=False
ALLOWED_HOSTS=issc.live,www.issc.live,YOUR_VPS_IP

# Database Configuration
DB_NAME=issc_db
DB_USER=issc_user
DB_PASSWORD=strong_password_here
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
```

**Save the file (Ctrl+O, Enter, Ctrl+X)**

**Generate a new SECRET_KEY:**
```bash
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```
Copy the output and use it for SECRET_KEY in .env

### Step 7.4: Update Django Settings for Production

```bash
cd /var/www/issc/issc
nano issc/settings.py
```

**Modify these settings:**

```python
# Change DEBUG to read from environment
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# Update ALLOWED_HOSTS
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Add CSRF trusted origins (add this new setting)
CSRF_TRUSTED_ORIGINS = [
    'https://issc.live',
    'https://www.issc.live',
]

# Update STATIC settings (around line 150)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Keep existing MEDIA and RECORDING settings
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

RECORDING_URL = '/recordings/'
RECORDING_ROOT = os.path.join(BASE_DIR, 'recordings')

# Add WhiteNoise for static files (already in MIDDLEWARE)
# Ensure this is in MIDDLEWARE list:
# 'whitenoise.middleware.WhiteNoiseMiddleware',

# Add at the bottom of settings.py:
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Security settings for production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

**Save and exit**

### Step 7.5: Install Python Dependencies

```bash
# Make sure virtual environment is activated
source /var/www/issc/venv/bin/activate

# Install all requirements
cd /var/www/issc
pip install -r requirements.txt

# Install production essentials
pip install gunicorn mysqlclient python-dotenv whitenoise
```

### Step 7.6: Django Database Migrations

```bash
cd /var/www/issc/issc

# Collect static files
python manage.py collectstatic --noinput

# Make migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
# Follow prompts to create admin account
```

### Step 7.7: Test Django Application

```bash
# Test if Django runs
python manage.py runserver 0.0.0.0:8000

# Open browser and visit: http://YOUR_VPS_IP:8000
# If it works, stop the server (Ctrl+C)
```

### Step 7.8: Set Proper Permissions

```bash
cd /var/www/issc

# Create necessary directories
mkdir -p media/files media/unauthorized_faces recordings

# Set ownership
sudo chown -R $USER:www-data /var/www/issc

# Set directory permissions
sudo find /var/www/issc -type d -exec chmod 755 {} \;

# Set file permissions
sudo find /var/www/issc -type f -exec chmod 644 {} \;

# Give write permissions to media and recordings
sudo chmod -R 775 media recordings
sudo chmod -R 775 issc/staticfiles
```

---

## 8. Configure Gunicorn Service

### Step 8.1: Create Gunicorn Socket File

```bash
sudo nano /etc/systemd/system/gunicorn.socket
```

**Add this content:**
```ini
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock

[Install]
WantedBy=sockets.target
```

**Save and exit**

### Step 8.2: Create Gunicorn Service File

```bash
sudo nano /etc/systemd/system/gunicorn.service
```

**Add this content (replace 'isscadmin' with your username):**
```ini
[Unit]
Description=gunicorn daemon for ISSC Django application
Requires=gunicorn.socket
After=network.target

[Service]
User=isscadmin
Group=www-data
WorkingDirectory=/var/www/issc/issc
Environment="PATH=/var/www/issc/venv/bin"
EnvironmentFile=/var/www/issc/.env
ExecStart=/var/www/issc/venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --timeout 120 \
          --bind unix:/run/gunicorn.sock \
          issc.wsgi:application

[Install]
WantedBy=multi-user.target
```

**Save and exit**

### Step 8.3: Start and Enable Gunicorn

```bash
# Start and enable Gunicorn socket
sudo systemctl start gunicorn.socket
sudo systemctl enable gunicorn.socket

# Check status
sudo systemctl status gunicorn.socket

# Check if socket file exists
file /run/gunicorn.sock
# Should show: /run/gunicorn.sock: socket

# Test Gunicorn
curl --unix-socket /run/gunicorn.sock localhost
```

---

## 9. Configure Nginx Web Server

### Step 9.1: Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/issc
```

**Add this configuration (replace 'yourdomain.com' with your actual domain):**
```nginx
server {
    listen 80;
    server_name issc.live www.issc.live;

    client_max_body_size 100M;

    # Logging
    access_log /var/log/nginx/issc_access.log;
    error_log /var/log/nginx/issc_error.log;

    # Static files
    location /static/ {
        alias /var/www/issc/issc/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /var/www/issc/issc/media/;
        expires 7d;
    }

    # Recordings
    location /recordings/ {
        alias /var/www/issc/issc/recordings/;
        expires 7d;
    }

    # Proxy to Gunicorn
    location / {
        proxy_pass http://unix:/run/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
    }
}
```

**Save and exit**

### Step 9.2: Enable the Site

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/issc /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# If OK, restart Nginx
sudo systemctl restart nginx

# Enable Nginx to start on boot
sudo systemctl enable nginx
```

### Step 9.3: Test HTTP Access

Open browser and visit:
- `http://yourdomain.com`
- `http://www.yourdomain.com`

You should see your Django application (without HTTPS yet).

---

## 10. SSL Certificate Setup (HTTPS)

### Step 10.1: Install Certbot

```bash
# Install Certbot and Nginx plugin
sudo apt install -y certbot python3-certbot-nginx
```

### Step 10.2: Obtain SSL Certificate

```bash
# Get certificate for your domain
sudo certbot --nginx -d issc.live -d www.issc.live
```

**Follow the prompts:**
- Enter email address (for renewal notifications)
- Agree to Terms of Service: **Y**
- Share email: **N** (optional)
- Redirect HTTP to HTTPS: **2** (recommended)

### Step 10.3: Verify SSL

Visit your site:
- `https://issc.live`

You should see the padlock icon indicating HTTPS is working.

### Step 10.4: Test Auto-Renewal

```bash
# Test certificate renewal
sudo certbot renew --dry-run

# If successful, certificate will auto-renew before expiration
```

### Step 10.5: Update Django Settings for SSL

```bash
nano /var/www/issc/.env
```

**Ensure DEBUG is False:**
```bash
DEBUG=False
```

**Restart Gunicorn:**
```bash
sudo systemctl restart gunicorn
```

---

## 11. Final Configuration & Testing

### Step 11.1: Create Systemd Services for Monitoring

**Create a script to monitor Gunicorn:**
```bash
sudo nano /usr/local/bin/issc_monitor.sh
```

**Add:**
```bash
#!/bin/bash
systemctl is-active --quiet gunicorn || systemctl restart gunicorn
systemctl is-active --quiet nginx || systemctl restart nginx
```

**Make executable:**
```bash
sudo chmod +x /usr/local/bin/issc_monitor.sh
```

### Step 11.2: Setup Cron Job for Monitoring

```bash
sudo crontab -e
```

**Add this line (runs every 5 minutes):**
```
*/5 * * * * /usr/local/bin/issc_monitor.sh
```

### Step 11.3: Configure Log Rotation

```bash
sudo nano /etc/logrotate.d/issc
```

**Add:**
```
/var/log/nginx/issc_*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
```

### Step 11.4: Test All Functionality

**Test checklist:**
- [ ] Homepage loads via HTTPS
- [ ] Admin panel accessible: `https://issc.live/admin/`
- [ ] Login system works
- [ ] Face recognition system works
- [ ] File uploads work
- [ ] Camera access works (if testing from local network)
- [ ] Incident reports can be created
- [ ] Email notifications work
- [ ] SMS notifications work (PhilSMS)

### Step 11.5: Performance Testing

```bash
# Test Gunicorn workers
sudo systemctl status gunicorn

# Monitor logs
sudo tail -f /var/log/nginx/issc_error.log
sudo journalctl -u gunicorn -f

# Check server resources
htop
# Install if not available: sudo apt install htop
```

---

## 12. Maintenance & Monitoring

### Daily Checks

```bash
# Check service status
sudo systemctl status nginx gunicorn

# Check disk usage
df -h

# Check memory
free -h

# View recent logs
sudo tail -100 /var/log/nginx/issc_error.log
```

### Weekly Tasks

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Check SSL certificate expiry
sudo certbot certificates

# Backup database
mysqldump -u issc_user -p issc_db > /var/backups/issc_db_$(date +%Y%m%d).sql
```

### Monthly Tasks

```bash
# Clean up old logs
sudo find /var/log -name "*.gz" -mtime +30 -delete

# Review security updates
sudo apt list --upgradable

# Test backup restoration
```

### Backup Strategy

**Create backup script:**
```bash
sudo nano /usr/local/bin/backup_issc.sh
```

**Add:**
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/issc"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
mysqldump -u issc_user -p'YOUR_DB_PASSWORD' issc_db > $BACKUP_DIR/db_$DATE.sql

# Backup media files
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /var/www/issc/issc/media

# Backup recordings
tar -czf $BACKUP_DIR/recordings_$DATE.tar.gz /var/www/issc/issc/recordings

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

**Make executable and schedule:**
```bash
sudo chmod +x /usr/local/bin/backup_issc.sh

# Add to crontab (daily at 2 AM)
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/backup_issc.sh >> /var/log/issc_backup.log 2>&1
```

---

## 13. Troubleshooting

### Issue 1: 502 Bad Gateway

**Cause:** Gunicorn not running or socket issue

**Solution:**
```bash
# Check Gunicorn status
sudo systemctl status gunicorn

# Restart Gunicorn
sudo systemctl restart gunicorn

# Check socket
sudo systemctl status gunicorn.socket

# View logs
sudo journalctl -u gunicorn -n 50
```

### Issue 2: Static Files Not Loading

**Solution:**
```bash
# Recollect static files
cd /var/www/issc/issc
source /var/www/issc/venv/bin/activate
python manage.py collectstatic --noinput

# Check permissions
sudo chown -R $USER:www-data /var/www/issc/issc/staticfiles
sudo chmod -R 755 /var/www/issc/issc/staticfiles

# Restart services
sudo systemctl restart gunicorn nginx
```

### Issue 3: Database Connection Error

**Solution:**
```bash
# Test MySQL connection
mysql -u issc_user -p issc_db

# Check .env file
cat /var/www/issc/.env | grep DB_

# Verify MySQL is running
sudo systemctl status mysql

# Check Django can connect
cd /var/www/issc/issc
source /var/www/issc/venv/bin/activate
python manage.py dbshell
```

### Issue 4: Permission Denied Errors

**Solution:**
```bash
# Fix ownership
sudo chown -R $USER:www-data /var/www/issc

# Fix permissions
sudo chmod -R 755 /var/www/issc
sudo chmod -R 775 /var/www/issc/issc/media
sudo chmod -R 775 /var/www/issc/issc/recordings
```

### Issue 5: SSL Certificate Issues

**Solution:**
```bash
# Renew certificate manually
sudo certbot renew

# Check certificate status
sudo certbot certificates

# Force renewal
sudo certbot renew --force-renewal
```

### Issue 6: Camera/Face Recognition Not Working

**Cause:** Missing OpenCV dependencies or permissions

**Solution:**
```bash
# Install missing dependencies
sudo apt install -y libgl1-mesa-glx libglib2.0-0

# Check camera permissions (if using USB camera)
sudo usermod -aG video $USER

# Reinstall OpenCV
source /var/www/issc/venv/bin/activate
pip uninstall opencv-python opencv-contrib-python
pip install opencv-python opencv-contrib-python

# Restart application
sudo systemctl restart gunicorn
```

### Issue 7: High Memory Usage

**Solution:**
```bash
# Reduce Gunicorn workers
sudo nano /etc/systemd/system/gunicorn.service
# Change --workers 3 to --workers 2

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart gunicorn

# Monitor memory
free -h
```

### Issue 8: Nginx Configuration Test Fails

**Solution:**
```bash
# Test configuration
sudo nginx -t

# Check error log
sudo tail -50 /var/log/nginx/error.log

# Verify syntax
sudo nginx -T
```

### Viewing Logs

```bash
# Nginx access logs
sudo tail -f /var/log/nginx/issc_access.log

# Nginx error logs
sudo tail -f /var/log/nginx/issc_error.log

# Gunicorn logs
sudo journalctl -u gunicorn -f

# System logs
sudo journalctl -xe

# Django application logs (if configured)
sudo tail -f /var/www/issc/issc/debug.log
```

---

## Quick Command Reference

### Service Management
```bash
# Restart all services
sudo systemctl restart gunicorn nginx mysql

# Check status
sudo systemctl status gunicorn nginx mysql

# View logs
sudo journalctl -u gunicorn -n 100
sudo tail -f /var/log/nginx/issc_error.log
```

### Django Management
```bash
# Activate virtual environment
cd /var/www/issc
source venv/bin/activate

# Collect static files
cd issc
python manage.py collectstatic --noinput

# Make migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Django shell
python manage.py shell
```

### File Permissions
```bash
# Reset permissions
sudo chown -R $USER:www-data /var/www/issc
sudo chmod -R 755 /var/www/issc
sudo chmod -R 775 /var/www/issc/issc/media
sudo chmod -R 775 /var/www/issc/issc/recordings
```

### Database Operations
```bash
# Backup database
mysqldump -u issc_user -p issc_db > backup_$(date +%Y%m%d).sql

# Restore database
mysql -u issc_user -p issc_db < backup_20240101.sql

# Access database
mysql -u issc_user -p issc_db
```

---

## Security Checklist

- [ ] Firewall (UFW) is enabled and configured
- [ ] Root login is disabled
- [ ] SSH uses key-based authentication (optional but recommended)
- [ ] MySQL root has strong password
- [ ] Database user has limited privileges
- [ ] DEBUG = False in production
- [ ] SECRET_KEY is strong and unique
- [ ] SSL certificate is installed and auto-renewing
- [ ] ALLOWED_HOSTS is properly configured
- [ ] CSRF protection is enabled
- [ ] Regular backups are automated
- [ ] Log monitoring is in place
- [ ] .env file is not in version control
- [ ] Sensitive credentials are in environment variables

---

## Performance Optimization Tips

### 1. Enable Gzip Compression in Nginx

```bash
sudo nano /etc/nginx/nginx.conf
```

Add in http block:
```nginx
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json;
```

### 2. Configure Django Caching

Add to settings.py:
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_table',
    }
}
```

Create cache table:
```bash
python manage.py createcachetable
```

### 3. Optimize Database

```sql
-- In MySQL
OPTIMIZE TABLE main_accountregistration;
OPTIMIZE TABLE main_facesembeddings;
OPTIMIZE TABLE main_incidentreport;
```

### 4. Monitor with htop

```bash
sudo apt install htop
htop
```

---

## Post-Deployment Updates

### Updating Your Application

```bash
# Pull latest changes (if using Git)
cd /var/www/issc
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install any new dependencies
pip install -r requirements.txt

# Collect static files
cd issc
python manage.py collectstatic --noinput

# Apply migrations
python manage.py migrate

# Restart services
sudo systemctl restart gunicorn
```

---

## Support Resources

### Useful Commands
- **Restart everything:** `sudo systemctl restart gunicorn nginx mysql`
- **Check all logs:** `sudo journalctl -xe`
- **Monitor resources:** `htop` or `top`
- **Check disk space:** `df -h`
- **Check internet:** `ping 8.8.8.8`

### Important File Locations
- Application: `/var/www/issc/`
- Virtual environment: `/var/www/issc/venv/`
- Django project: `/var/www/issc/issc/`
- Nginx config: `/etc/nginx/sites-available/issc`
- Gunicorn service: `/etc/systemd/system/gunicorn.service`
- Environment variables: `/var/www/issc/.env`
- Logs: `/var/log/nginx/` and `sudo journalctl -u gunicorn`

### Emergency Recovery

If site goes down:
```bash
# 1. Check service status
sudo systemctl status gunicorn nginx mysql

# 2. Restart services
sudo systemctl restart gunicorn nginx

# 3. Check logs
sudo tail -100 /var/log/nginx/issc_error.log
sudo journalctl -u gunicorn -n 100

# 4. Verify .env file exists
cat /var/www/issc/.env

# 5. Test database connection
mysql -u issc_user -p issc_db
```

---

## Conclusion

Your ISSC Django system should now be fully deployed and accessible via:
- **HTTPS:** `https://issc.live`
- **Admin Panel:** `https://issc.live/admin/`

**Next Steps:**
1. Test all features thoroughly
2. Set up regular backups
3. Monitor logs daily for first week
4. Configure email alerts for errors
5. Document any custom configurations
6. Train users on the system

**Remember:**
- Always backup before making changes
- Test updates in development first
- Monitor server resources regularly
- Keep system and dependencies updated
- Review security logs weekly

---

**Created:** December 4, 2025  
**Version:** 1.0  
**System:** ISSC Django Face Recognition System  
**Target:** Hostinger KVM2 VPS + Ubuntu 24.04 + Namecheap Domain
