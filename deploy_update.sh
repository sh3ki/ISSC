#!/bin/bash
# ISSC Deployment Update Script
# Run this on Ubuntu server to update code and fix email/SMS

echo "=========================================="
echo "ISSC Deployment Update Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/root/ISSC/issc"
VENV_DIR="/root/ISSC/venv"
SERVICE_NAME="gunicorn"

echo -e "${YELLOW}Step 1: Stopping Gunicorn service...${NC}"
systemctl stop $SERVICE_NAME
sleep 2

echo -e "${GREEN}✓ Service stopped${NC}"
echo ""

echo -e "${YELLOW}Step 2: Backing up current code...${NC}"
BACKUP_DIR="/root/ISSC_backup_$(date +%Y%m%d_%H%M%S)"
cp -r $PROJECT_DIR $BACKUP_DIR
echo -e "${GREEN}✓ Backup created at: $BACKUP_DIR${NC}"
echo ""

echo -e "${YELLOW}Step 3: Pulling latest changes from Git...${NC}"
cd /root/ISSC
git pull origin master
echo -e "${GREEN}✓ Code updated from Git${NC}"
echo ""

echo -e "${YELLOW}Step 4: Activating virtual environment...${NC}"
source $VENV_DIR/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

echo -e "${YELLOW}Step 5: Installing/updating Python packages...${NC}"
pip install --upgrade pip
pip install -r /root/ISSC/requirements.txt
echo -e "${GREEN}✓ Packages updated${NC}"
echo ""

echo -e "${YELLOW}Step 6: Checking .env file configuration...${NC}"
if [ -f "$PROJECT_DIR/.env" ]; then
    echo -e "${GREEN}✓ .env file exists${NC}"
    
    # Check for required email/SMS variables
    echo ""
    echo "Checking EMAIL configuration..."
    if grep -q "EMAIL_HOST_USER=" "$PROJECT_DIR/.env"; then
        EMAIL_USER=$(grep "EMAIL_HOST_USER=" "$PROJECT_DIR/.env" | cut -d '=' -f2)
        echo -e "${GREEN}✓ EMAIL_HOST_USER found: $EMAIL_USER${NC}"
    else
        echo -e "${RED}✗ EMAIL_HOST_USER not found in .env${NC}"
    fi
    
    if grep -q "EMAIL_HOST_PASSWORD=" "$PROJECT_DIR/.env"; then
        echo -e "${GREEN}✓ EMAIL_HOST_PASSWORD found (hidden)${NC}"
    else
        echo -e "${RED}✗ EMAIL_HOST_PASSWORD not found in .env${NC}"
    fi
    
    echo ""
    echo "Checking PhilSMS configuration..."
    if grep -q "PHILSMS_API_TOKEN=" "$PROJECT_DIR/.env"; then
        echo -e "${GREEN}✓ PHILSMS_API_TOKEN found${NC}"
    else
        echo -e "${RED}✗ PHILSMS_API_TOKEN not found in .env${NC}"
    fi
    
    if grep -q "PHILSMS_RECIPIENT=" "$PROJECT_DIR/.env"; then
        PHILSMS_RECIPIENT=$(grep "PHILSMS_RECIPIENT=" "$PROJECT_DIR/.env" | cut -d '=' -f2)
        echo -e "${GREEN}✓ PHILSMS_RECIPIENT found: $PHILSMS_RECIPIENT${NC}"
    else
        echo -e "${RED}✗ PHILSMS_RECIPIENT not found in .env${NC}"
    fi
else
    echo -e "${RED}✗ .env file not found!${NC}"
    echo ""
    echo "Creating .env file template..."
    cat > "$PROJECT_DIR/.env" << 'EOF'
# Django Settings
SECRET_KEY='GENERATE_NEW_SECRET_KEY_HERE'
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
EOF
    echo -e "${GREEN}✓ .env template created${NC}"
    echo -e "${YELLOW}⚠ Please edit $PROJECT_DIR/.env and configure your values${NC}"
fi
echo ""

echo -e "${YELLOW}Step 7: Running Django migrations...${NC}"
cd $PROJECT_DIR
python manage.py migrate
echo -e "${GREEN}✓ Migrations complete${NC}"
echo ""

echo -e "${YELLOW}Step 8: Collecting static files...${NC}"
python manage.py collectstatic --noinput
echo -e "${GREEN}✓ Static files collected${NC}"
echo ""

echo -e "${YELLOW}Step 9: Setting permissions...${NC}"
chown -R www-data:www-data $PROJECT_DIR
chmod -R 755 $PROJECT_DIR
echo -e "${GREEN}✓ Permissions set${NC}"
echo ""

echo -e "${YELLOW}Step 10: Starting Gunicorn service...${NC}"
systemctl start $SERVICE_NAME
sleep 3
systemctl status $SERVICE_NAME --no-pager
echo -e "${GREEN}✓ Service started${NC}"
echo ""

echo -e "${YELLOW}Step 11: Reloading Nginx...${NC}"
systemctl reload nginx
echo -e "${GREEN}✓ Nginx reloaded${NC}"
echo ""

echo "=========================================="
echo -e "${GREEN}Deployment Update Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Test email functionality"
echo "2. Test SMS functionality"
echo "3. Check application logs if issues occur:"
echo "   - journalctl -u gunicorn -n 50 --no-pager"
echo "   - tail -f /var/log/nginx/error.log"
echo ""
