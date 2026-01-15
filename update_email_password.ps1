# Update Gmail App Password on Production Server
# Usage: .\update_email_password.ps1 "your-new-16-char-password"

param(
    [Parameter(Mandatory=$true)]
    [string]$NewPassword
)

Write-Host "Updating Gmail app password on production server..." -ForegroundColor Green

# SSH and update the .env file
ssh root@72.62.66.193 @"
cd /var/www/issc
sed -i 's/^EMAIL_HOST_PASSWORD=.*/EMAIL_HOST_PASSWORD=$NewPassword/' .env
echo "Updated password in .env"
cat .env | grep EMAIL_HOST_PASSWORD
systemctl restart gunicorn
echo "Gunicorn restarted"
"@

Write-Host "`nTesting email with new password..." -ForegroundColor Yellow

ssh root@72.62.66.193 @"
cd /var/www/issc && source venv/bin/activate && cd /root/ISSC && python test_email_sms.py 2>&1 | grep -A15 'Testing Email'
"@

Write-Host "`nDone!" -ForegroundColor Green
