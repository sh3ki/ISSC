# ISSC Server Deployment Update Guide
## Fix Email & SMS on Ubuntu VPS

---

## Quick Start

Connect to your server:
```bash
ssh root@72.62.66.193
```

---

## Step 1: Upload Files to Server

From your **local computer** (Windows PowerShell), upload the deployment scripts:

```powershell
# Navigate to ISSC project folder
cd C:\Users\USER\Downloads\ISSC-Django-main

# Upload deployment script
scp deploy_update.sh root@72.62.66.193:/root/

# Upload test script  
scp test_email_sms.py root@72.62.66.193:/root/
```

---

## Step 2: Check Current .env File

On the **server**:

```bash
cd /root/ISSC/issc
cat .env
```

**If .env file exists**, verify it has these variables:
```bash
EMAIL_HOST_USER=vinceerickquiozon14@gmail.com
EMAIL_HOST_PASSWORD=viqbpwklhlergez
PHILSMS_API_BASE=https://dashboard.philsms.com/api/v3
PHILSMS_API_TOKEN=377|DT0C9GeHCgLXdNt5oxjajd3QqdLlKcqMHv5KLZcE3b45ab96
PHILSMS_SENDER_ID=PhilSMS
PHILSMS_RECIPIENT=09945349194
PHILSMS_COOLDOWN_SECONDS=900
```

**If .env file is missing or incomplete**, create/edit it:

```bash
cd /root/ISSC/issc
nano .env
```

Add all the configuration above, then save (Ctrl+O, Enter, Ctrl+X).

---

## Step 3: Update Django settings.py

Ensure settings.py reads from environment variables:

```bash
cd /root/ISSC/issc/issc
nano settings.py
```

**Verify these settings exist** (scroll to bottom of file):

```python
# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER') or 'vinceerickquiozon14@gmail.com'
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD') or 'viqbpwklhlergez'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# PhilSMS Configuration (if needed in settings)
PHILSMS_API_BASE = os.getenv('PHILSMS_API_BASE', 'https://dashboard.philsms.com/api/v3')
PHILSMS_API_TOKEN = os.getenv('PHILSMS_API_TOKEN', '377|DT0C9GeHCgLXdNt5oxjajd3QqdLlKcqMHv5KLZcE3b45ab96')
PHILSMS_SENDER_ID = os.getenv('PHILSMS_SENDER_ID', 'PhilSMS')
PHILSMS_RECIPIENT = os.getenv('PHILSMS_RECIPIENT', '09945349194')
PHILSMS_COOLDOWN_SECONDS = int(os.getenv('PHILSMS_COOLDOWN_SECONDS', '900'))
```

If missing, add them at the end of the file. Save and exit.

---

## Step 4: Run Deployment Update Script

```bash
cd /root
chmod +x deploy_update.sh
./deploy_update.sh
```

This script will:
- Stop Gunicorn
- Backup current code
- Update dependencies
- Check .env configuration
- Run migrations
- Collect static files
- Restart services

---

## Step 5: Test Email and SMS

```bash
cd /root
chmod +x test_email_sms.py
python3 test_email_sms.py
```

**Expected output:**
```
📧 Testing Email Configuration...
Sending test email...
✅ Email sent successfully!

📱 Testing PhilSMS Configuration...
Sending test SMS...
Status Code: 200
✅ SMS sent successfully!
```

---

## Step 6: Check Firewall (if tests fail)

Ensure server can access external services:

```bash
# Check firewall status
sudo ufw status

# Allow outgoing connections (if needed)
sudo ufw allow out 587/tcp    # SMTP for Gmail
sudo ufw allow out 443/tcp    # HTTPS for PhilSMS

# Test Gmail SMTP connectivity
telnet smtp.gmail.com 587

# Test PhilSMS API connectivity
curl -I https://dashboard.philsms.com/api/v3
```

---

## Step 7: Verify Services are Running

```bash
# Check Gunicorn status
systemctl status gunicorn

# Check Nginx status
systemctl status nginx

# View recent logs
journalctl -u gunicorn -n 50 --no-pager

# Check Nginx error log
tail -f /var/log/nginx/error.log
```

---

## Troubleshooting

### Email Not Working

1. **Check Gmail App Password**:
   - Password should be exactly: `viqbpwklhlergez`
   - No spaces, no special characters
   - Verify in .env file

2. **Check Gmail Account Settings**:
   - 2-Step Verification must be enabled
   - App Password must be generated for "Mail"
   - Account must not have "Less secure app access" enabled

3. **Test SMTP Connection**:
```bash
python3 -c "import smtplib; s=smtplib.SMTP('smtp.gmail.com', 587); s.starttls(); s.login('vinceerickquiozon14@gmail.com', 'viqbpwklhlergez'); print('✅ SMTP works!'); s.quit()"
```

### SMS Not Working

1. **Check PhilSMS Credits**:
   - Login to https://dashboard.philsms.com/
   - Verify account has credits

2. **Check API Token**:
   - Token: `377|DT0C9GeHCgLXdNt5oxjajd3QqdLlKcqMHv5KLZcE3b45ab96`
   - Must be valid and not expired

3. **Test PhilSMS API**:
```bash
curl -X POST https://dashboard.philsms.com/api/v3/sms/send \
  -H "Authorization: Bearer 377|DT0C9GeHCgLXdNt5oxjajd3QqdLlKcqMHv5KLZcE3b45ab96" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": "09945349194",
    "sender_id": "PhilSMS",
    "type": "plain",
    "message": "Test SMS from ISSC server"
  }'
```

### General Issues

1. **Restart Everything**:
```bash
systemctl restart gunicorn
systemctl restart nginx
```

2. **Check Django Can Load .env**:
```bash
cd /root/ISSC/issc
source /root/ISSC/venv/bin/activate
python manage.py shell
>>> from django.conf import settings
>>> print(settings.EMAIL_HOST_USER)
>>> print(settings.EMAIL_HOST_PASSWORD)
>>> exit()
```

3. **Check File Permissions**:
```bash
ls -la /root/ISSC/issc/.env
# Should be readable by www-data or gunicorn user
```

---

## Quick Commands Reference

```bash
# Connect to server
ssh root@72.62.66.193

# View application logs
journalctl -u gunicorn -n 100 --no-pager

# Restart services
systemctl restart gunicorn
systemctl restart nginx

# Test email/SMS
python3 /root/test_email_sms.py

# Edit .env file
nano /root/ISSC/issc/.env

# Check service status
systemctl status gunicorn --no-pager
systemctl status nginx --no-pager
```

---

## Success Checklist

- [ ] .env file exists with EMAIL and PHILSMS variables
- [ ] settings.py reads from environment variables
- [ ] Test script shows ✅ for both email and SMS
- [ ] Gunicorn service is running
- [ ] Nginx service is running
- [ ] No errors in `journalctl -u gunicorn -n 50`
- [ ] Website loads correctly at issc.live

---

## Need Help?

If you encounter issues:
1. Run the test script and share the output
2. Check logs: `journalctl -u gunicorn -n 50 --no-pager`
3. Verify .env file: `cat /root/ISSC/issc/.env`
4. Test connectivity to Gmail SMTP and PhilSMS API

