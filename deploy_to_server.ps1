# Quick deployment to Ubuntu server
Write-Host "Deploying to server 72.62.66.193..." -ForegroundColor Green

# SSH to server and run deployment
ssh root@72.62.66.193 @"
cd /root/ISSC/issc
chmod +x deploy_update.sh
./deploy_update.sh
"@

Write-Host "`nDeployment complete! Now testing email and SMS..." -ForegroundColor Green

# Test email and SMS
ssh root@72.62.66.193 @"
cd /root/ISSC/issc
python3 test_email_sms.py
"@

Write-Host "`nAll done!" -ForegroundColor Green
