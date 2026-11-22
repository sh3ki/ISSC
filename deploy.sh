#!/usr/bin/env bash
# ISSC-only production deployment.
# Run on the VPS from /var/www/issc as root: bash deploy.sh

set -Eeuo pipefail

APP_DIR="/var/www/issc"
PROJECT_DIR="$APP_DIR/issc"
VENV_DIR="$APP_DIR/venv"
ENV_FILE="$APP_DIR/.env"
MAINTENANCE_FLAG="/var/lib/issc/maintenance.flag"
SERVICE="issc-gunicorn.service"
BRANCH="${1:-master}"

log() { printf '\n[%s] %s\n' "$(date '+%F %T')" "$*"; }
fail() { log "ERROR: $*" >&2; exit 1; }

[[ "${EUID}" -eq 0 ]] || fail "Run this script as root."
[[ -d "$APP_DIR/.git" ]] || fail "Missing Git repository: $APP_DIR"
[[ -f "$PROJECT_DIR/manage.py" ]] || fail "Missing Django project: $PROJECT_DIR/manage.py"
[[ -x "$VENV_DIR/bin/python" ]] || fail "Missing virtualenv: $VENV_DIR"
[[ -f "$ENV_FILE" ]] || fail "Missing production environment file: $ENV_FILE"

mkdir -p "$(dirname "$MAINTENANCE_FLAG")"
exec 9>/run/lock/issc-deploy.lock
flock -n 9 || fail "Another ISSC deployment is already running."

maintenance_on() {
    touch "$MAINTENANCE_FLAG"
    systemctl reload nginx
}

maintenance_off() {
    rm -f "$MAINTENANCE_FLAG"
    systemctl reload nginx
}

on_error() {
    local code=$?
    log "Deployment failed with exit code $code. ISSC remains in maintenance mode for safety."
    log "Inspect: journalctl -u $SERVICE -n 100 --no-pager"
    exit "$code"
}
trap on_error ERR

log "Checking the ISSC checkout before taking it offline"
cd "$APP_DIR"
git fetch --prune origin "$BRANCH"

if [[ -n "$(git status --porcelain)" ]]; then
    STASH_NAME="issc-deploy-local-$(date +%Y%m%d_%H%M%S)"
    log "Stashing local checkout changes as $STASH_NAME"
    git status --short
    git stash push --include-untracked --message "$STASH_NAME"
    log "Local changes were stashed. Restore them later with: git stash pop"
fi

log "Enabling ISSC maintenance mode"
maintenance_on

log "Stopping only $SERVICE"
systemctl stop "$SERVICE" || true

log "Pulling origin/$BRANCH"
git pull --ff-only origin "$BRANCH"

log "Installing Python dependencies"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$APP_DIR/requirements.txt"

log "Running Django checks and migrations"
cd "$PROJECT_DIR"
"$VENV_DIR/bin/python" manage.py check --deploy
"$VENV_DIR/bin/python" manage.py migrate --noinput

log "Collecting static files"
"$VENV_DIR/bin/python" manage.py collectstatic --noinput

log "Ensuring writable ISSC runtime directories"
RUNTIME_DIRS=(
    "$PROJECT_DIR/media"
    "$PROJECT_DIR/media/files"
    "$PROJECT_DIR/media/images"
    "$PROJECT_DIR/media/recordings"
    "$PROJECT_DIR/media/unauthorized_faces"
    "$PROJECT_DIR/recordings"
    "$PROJECT_DIR/backups"
    "$PROJECT_DIR/backups/deleted"
)

for runtime_dir in "${RUNTIME_DIRS[@]}"; do
    install -d -o isscadmin -g www-data -m 2775 "$runtime_dir"
done

for runtime_root in "$PROJECT_DIR/media" "$PROJECT_DIR/recordings" "$PROJECT_DIR/backups"; do
    chown -R isscadmin:www-data "$runtime_root"
    find "$runtime_root" -type d -exec chmod 2775 {} +
    find "$runtime_root" -type f -exec chmod 0664 {} +
done

log "Starting only $SERVICE"
systemctl start "$SERVICE"
systemctl is-active --quiet "$SERVICE"

log "Checking ISSC through its Unix socket"
for attempt in {1..20}; do
    code="$(curl --silent --output /dev/null --write-out '%{http_code}' \
        --unix-socket /run/issc-gunicorn/gunicorn.sock \
        -H 'Host: issc.click' http://localhost/ || true)"
    if [[ "$code" =~ ^[23][0-9][0-9]$ ]]; then
        log "ISSC responded with HTTP $code"
        maintenance_off
        log "ISSC deployment completed successfully"
        exit 0
    fi
    sleep 2
done

fail "ISSC did not become healthy. Maintenance mode remains enabled."
