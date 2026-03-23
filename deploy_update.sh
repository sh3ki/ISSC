#!/bin/bash
# ISSC deployment update script for the live server.
# Updates backend + frontend (templates/static), applies migrations,
# and restarts services safely.

set -euo pipefail

echo "=========================================="
echo "ISSC Deployment Update Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration (actual live paths)
REPO_DIR="/var/www/issc"
PROJECT_DIR="/var/www/issc/issc"
VENV_DIR="/var/www/issc/venv"
SERVICE_NAME="gunicorn"
BRANCH="master"

require_path() {
    local p="$1"
    local label="$2"
    if [ ! -e "$p" ]; then
        echo -e "${RED}✗ Missing ${label}: ${p}${NC}"
        exit 1
    fi
}

echo -e "${YELLOW}Step 1: Validating environment paths...${NC}"
require_path "$REPO_DIR/.git" "git repository"
require_path "$PROJECT_DIR/manage.py" "Django project"
require_path "$VENV_DIR/bin/activate" "Python virtualenv"
echo -e "${GREEN}✓ Paths validated${NC}"
echo ""

echo -e "${YELLOW}Step 2: Stashing local changes (if any)...${NC}"
cd "$REPO_DIR"
if [ -n "$(git status --porcelain)" ]; then
    STASH_NAME="auto-update-$(date +%Y%m%d_%H%M%S)"
    git stash push -u -m "$STASH_NAME"
    echo -e "${GREEN}✓ Local changes stashed as: ${STASH_NAME}${NC}"
else
    echo -e "${GREEN}✓ Working tree is clean, nothing to stash${NC}"
fi
echo ""

echo -e "${YELLOW}Step 3: Pulling latest code from origin/${BRANCH}...${NC}"
git pull origin "$BRANCH"
echo -e "${GREEN}✓ Code updated from Git${NC}"
echo ""

echo -e "${YELLOW}Step 4: Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

echo -e "${YELLOW}Step 5: Installing/updating Python dependencies...${NC}"
pip install -r "$REPO_DIR/requirements.txt"
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

echo -e "${YELLOW}Step 6: Running database migrations...${NC}"
cd "$PROJECT_DIR"
python manage.py migrate --noinput
echo -e "${GREEN}✓ Migrations complete${NC}"
echo ""

echo -e "${YELLOW}Step 7: Collecting static files (frontend assets)...${NC}"
python manage.py collectstatic --noinput
echo -e "${GREEN}✓ Static files collected${NC}"
echo ""

echo -e "${YELLOW}Step 8: Restarting backend service...${NC}"
systemctl restart "$SERVICE_NAME"
systemctl is-active --quiet "$SERVICE_NAME"
echo -e "${GREEN}✓ ${SERVICE_NAME} is running${NC}"
echo ""

echo -e "${YELLOW}Step 9: Reloading Nginx...${NC}"
systemctl reload nginx
echo -e "${GREEN}✓ Nginx reloaded${NC}"
echo ""

echo "=========================================="
echo -e "${GREEN}Deployment Update Complete!${NC}"
echo "=========================================="
echo ""
echo "Useful follow-up commands:"
echo "- Show stashes: git -C $REPO_DIR stash list"
echo "- Gunicorn logs: journalctl -u $SERVICE_NAME -n 80 --no-pager"
echo "- Nginx logs: tail -n 80 /var/log/nginx/error.log"
echo ""
