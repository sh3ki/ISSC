#!/bin/bash
# ISSC Production Deployment Script with Database Configuration

echo "=========================================="
echo "ISSC Production Deployment Script"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Paths
GIT_REPO="/root/ISSC"
PRODUCTION_DIR="/var/www/issc/issc"
PRODUCTION_ENV_FILE="/var/www/issc/issc/issc/.env"

echo -e "${YELLOW}Step 1: Navigating to git repository...${NC}"
cd $GIT_REPO || { echo -e "${RED}Failed to navigate to git repo${NC}"; exit 1; }
echo -e "${GREEN}✓ In git repository${NC}"
echo ""

echo -e "${YELLOW}Step 2: Stashing local changes...${NC}"
git stash
echo -e "${GREEN}✓ Local changes stashed${NC}"
echo ""

echo -e "${YELLOW}Step 3: Pulling latest changes from Git...${NC}"
git pull origin master
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Git pull failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Latest changes pulled${NC}"
echo ""

echo -e "${YELLOW}Step 4: Syncing to production directory...${NC}"
rsync -av --exclude='.git' \
          --exclude='*.pyc' \
          --exclude='__pycache__' \
          --exclude='media/' \
          --exclude='recordings/' \
          --exclude='issc/.env' \
          ./issc/ $PRODUCTION_DIR/
echo -e "${GREEN}✓ Files synced to production${NC}"
echo ""

echo -e "${YELLOW}Step 5: Configuring production .env file...${NC}"
# Create .env file with production settings
cat > "$PRODUCTION_ENV_FILE" << 'EOF'
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

echo -e "${GREEN}✓ Production .env file configured${NC}"
echo -e "${GREEN}  - Database: issc${NC}"
echo -e "${GREEN}  - User: issc_user${NC}"
echo -e "${GREEN}  - Password: Issc@2024${NC}"
echo ""

echo -e "${YELLOW}Step 6: Setting proper permissions...${NC}"
chown -R www-data:www-data $PRODUCTION_DIR
chmod -R 755 $PRODUCTION_DIR
chmod 640 "$PRODUCTION_ENV_FILE"  # Readable by www-data
chown www-data:www-data "$PRODUCTION_ENV_FILE"
echo -e "${GREEN}✓ Permissions set${NC}"
echo ""

echo -e "${YELLOW}Step 7: Running Django migrations...${NC}"
cd $PRODUCTION_DIR
source /var/www/issc/venv/bin/activate
python manage.py migrate --noinput
echo -e "${GREEN}✓ Migrations complete${NC}"
echo ""

echo -e "${YELLOW}Step 8: Collecting static files...${NC}"
python manage.py collectstatic --noinput
echo -e "${GREEN}✓ Static files collected${NC}"
echo ""

echo -e "${YELLOW}Step 9: Restarting Gunicorn...${NC}"
systemctl restart gunicorn
sleep 3
echo -e "${GREEN}✓ Gunicorn restarted${NC}"
echo ""

echo -e "${YELLOW}Step 10: Checking Gunicorn status...${NC}"
systemctl status gunicorn --no-pager
echo ""

echo -e "${YELLOW}Step 11: Reloading Nginx...${NC}"
systemctl reload nginx
echo -e "${GREEN}✓ Nginx reloaded${NC}"
echo ""

echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Database Configuration:"
echo "  - Host: 127.0.0.1:3306"
echo "  - Database: issc"
echo "  - User: issc_user"
echo "  - Password: Issc@2024"
echo ""
echo "If you see errors, check:"
echo "  - journalctl -u gunicorn -n 50 --no-pager"
echo "  - tail -f /var/log/nginx/error.log"
echo ""
