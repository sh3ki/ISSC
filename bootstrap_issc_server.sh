#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR=/var/www/issc
SERVICE_USER=isscadmin
DB_NAME=issc_db
DB_USER=issc_user

[[ $EUID -eq 0 ]] || { echo 'Run as root'; exit 1; }
[[ ! -e "$APP_DIR" ]] || { echo "$APP_DIR already exists; refusing to overwrite it"; exit 1; }

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
  git curl ca-certificates build-essential pkg-config \
  python3.12 python3.12-venv python3.12-dev \
  default-libmysqlclient-dev libgeos-dev \
  libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
  libjpeg-dev zlib1g-dev libtiff-dev libfreetype6-dev liblcms2-dev libwebp-dev \
  ffmpeg certbot python3-certbot-nginx

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

git clone --branch master --single-branch https://github.com/sh3ki/ISSC.git "$APP_DIR"
python3.12 -m venv "$APP_DIR/venv"

DB_PASSWORD=$(openssl rand -hex 24)
SECRET_KEY=$(openssl rand -hex 48)

mysql --protocol=socket -uroot <<SQL
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
ALTER USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

cat > "$APP_DIR/.env" <<EOF
SECRET_KEY=$SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=issc.click,www.issc.click,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://issc.click,https://www.issc.click
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_HOST=127.0.0.1
DB_PORT=3306
CAMERA_AUTO_START=0
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=
PHILSMS_API_BASE=https://dashboard.philsms.com/api/v3
PHILSMS_API_TOKEN=
PHILSMS_SENDER_ID=PhilSMS
PHILSMS_RECIPIENT=
PHILSMS_COOLDOWN_SECONDS=900
EOF

chown -R root:"$SERVICE_USER" "$APP_DIR"
chmod 750 "$APP_DIR"
chmod 640 "$APP_DIR/.env"
mkdir -p /var/lib/issc
chown "$SERVICE_USER":www-data /var/lib/issc
chmod 775 /var/lib/issc

echo 'ISSC base installation complete.'
