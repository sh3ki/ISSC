# Backup System - Quick Reference

## Quick Start

### 1. Access Backup Page
- Login as Admin → Click "Backup" in sidebar menu
- URL: `http://localhost:9000/backup/`

### 2. Create Manual Backup
- Click the **"Create Backup Now"** button
- Wait for completion (5-30 seconds)
- Backup appears in the table below

### 3. Download Backup
- Find backup in table
- Click green **"Download"** button
- SQL file downloads to your Downloads folder

### 4. Setup Automatic Backups

**Windows:**
```powershell
# Run as Administrator
cd C:\Users\USER\Downloads\ISSC-Django-main
powershell -ExecutionPolicy Bypass -File setup_backup_scheduler.ps1
```

**Linux (Ubuntu 24.04):**
```bash
cd /var/www/issc
chmod +x setup_backup_scheduler_linux.sh
sudo ./setup_backup_scheduler_linux.sh
```

## Commands

### Create Manual Backup
```bash
cd issc
python manage.py auto_backup
```

### Create Backup with Cleanup
```bash
python manage.py auto_backup --cleanup --keep-days 30
```

### Test Backup System
```bash
# Windows
cd issc
python manage.py auto_backup

# Linux
cd /var/www/issc/issc
/var/www/issc/venv/bin/python manage.py auto_backup
```

## Backup Locations

**Windows Local:**
```
C:\Users\USER\Downloads\ISSC-Django-main\backups\
```

**Linux Production:**
```
/var/www/issc/backups/
```

## Restore Database

**MySQL:**
```bash
# Windows
mysql -u issc_user -p issc_db < backups\backup_file.sql

# Linux
mysql -u issc_user -p issc_db < /var/www/issc/backups/backup_file.sql
```

**SQLite:**
```bash
# Windows
copy backups\backup_file.sql issc\db.sqlite3

# Linux
cp /var/www/issc/backups/backup_file.sql /var/www/issc/issc/db.sqlite3
```

## Check Status

**Windows - Check Scheduled Task:**
```powershell
Get-ScheduledTask -TaskName "ISSC_AutoBackup"
```

**Linux - Check Cron Job:**
```bash
crontab -l | grep issc
```

**Linux - View Logs:**
```bash
tail -f /var/log/issc_backup.log
```

## Troubleshooting

### mysqldump not found

**Windows:**
- Install MySQL Server or MySQL Workbench
- Add to PATH: `C:\Program Files\MySQL\MySQL Server 8.0\bin`

**Linux:**
```bash
sudo apt install mysql-client
```

### Permission Denied

**Linux:**
```bash
sudo chown -R www-data:www-data /var/www/issc/backups
sudo chmod -R 755 /var/www/issc/backups
```

### Check Timezone

**Windows:**
```powershell
Get-TimeZone
Set-TimeZone -Id "Singapore Standard Time"  # Manila uses this
```

**Linux:**
```bash
timedatectl
sudo timedatectl set-timezone Asia/Manila
```

## File Structure

```
ISSC-Django-main/
├── backups/                           # Backup storage directory
│   ├── issc_backup_auto_*.sql        # Automatic backups
│   └── issc_backup_manual_*.sql      # Manual backups
├── issc/
│   └── main/
│       ├── views/
│       │   └── backup_view.py        # Backup logic
│       ├── templates/
│       │   └── backup.html           # Backup UI
│       └── management/
│           └── commands/
│               └── auto_backup.py    # Auto backup command
├── setup_backup_scheduler.ps1         # Windows scheduler
└── setup_backup_scheduler_linux.sh    # Linux scheduler
```

## URLs

- **Backup Page**: `/backup/`
- **Create Backup**: `/backup/create/` (AJAX POST)
- **Download**: `/backup/download/<filename>/`
- **Delete**: `/backup/delete/<filename>/` (POST)

## Features

✅ Automatic daily backups at 00:00 (Manila time)
✅ Manual backup button
✅ Backup history table with search & sort
✅ Download backups as SQL files
✅ Delete old backups
✅ Auto-cleanup (30 days for automatic backups)
✅ Works on Windows & Linux
✅ Supports MySQL & SQLite

## Important Notes

1. **Only admin users** can access the backup page
2. **Automatic backups** run at midnight (00:00) Asia/Manila time
3. **Manual backups** are never auto-deleted
4. **Automatic backups** older than 30 days are auto-deleted
5. **Backup files** are stored as plain SQL dumps

## Support

For detailed information, see: `BACKUP_SYSTEM_GUIDE.md`
