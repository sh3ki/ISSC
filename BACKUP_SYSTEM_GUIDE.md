# Database Backup System - Complete Guide

## Overview

The ISSC system now includes a comprehensive database backup solution with both automatic and manual backup capabilities. This system works on Windows local servers, Windows production servers, and Ubuntu 24.04 Linux servers.

## Features

✅ **Automatic Daily Backups** - Runs every day at 00:00 (midnight) Asia/Manila time
✅ **Manual Backup Button** - Create backups on-demand with one click
✅ **Backup History Table** - View all backups with type, size, and creation date
✅ **Download Backups** - Download any backup file as SQL
✅ **Delete Old Backups** - Remove unnecessary backup files
✅ **Automatic Cleanup** - Old automatic backups (30+ days) are auto-deleted
✅ **Cross-Platform** - Works on Windows and Linux (Ubuntu 24.04)
✅ **Database Support** - Supports both MySQL and SQLite databases

## Files Created

### 1. Backend View
- **File**: `issc/main/views/backup_view.py`
- **Purpose**: Handles backup creation, listing, download, and deletion
- **Functions**:
  - `backup_page()` - Main backup page view
  - `create_manual_backup()` - AJAX endpoint for manual backups
  - `download_backup()` - Download backup files
  - `delete_backup()` - Delete backup files
  - `create_backup()` - Core backup creation logic
  - `get_backup_list()` - List all backup files

### 2. Template
- **File**: `issc/main/templates/backup.html`
- **Purpose**: Beautiful UI for backup management
- **Features**:
  - Real-time Manila timezone clock
  - Statistics cards (total backups, total size, schedule)
  - Manual backup button with loading state
  - Sortable table with DataTables
  - Download and delete actions per backup
  - Alert notifications

### 3. URL Configuration
- **File**: `issc/main/urls.py`
- **Added Routes**:
  - `/backup/` - Backup management page
  - `/backup/create/` - Create manual backup (AJAX)
  - `/backup/download/<filename>/` - Download backup
  - `/backup/delete/<filename>/` - Delete backup

### 4. Management Command
- **File**: `issc/main/management/commands/auto_backup.py`
- **Purpose**: Django management command for automatic backups
- **Usage**: `python manage.py auto_backup`
- **Options**:
  - `--cleanup` - Remove backups older than specified days
  - `--keep-days N` - Number of days to keep (default: 30)

### 5. Windows Scheduler Setup
- **File**: `setup_backup_scheduler.ps1`
- **Purpose**: Creates Windows Task Scheduler task
- **Schedule**: Daily at 00:00
- **Requirements**: Run as Administrator

### 6. Linux Scheduler Setup
- **File**: `setup_backup_scheduler_linux.sh`
- **Purpose**: Creates cron job for automatic backups
- **Schedule**: Daily at 00:00
- **Requirements**: Run with sudo

## Installation Instructions

### For Windows (Local or Production)

1. **Install the scheduler** (run as Administrator):
   ```powershell
   cd C:\Users\USER\Downloads\ISSC-Django-main
   powershell -ExecutionPolicy Bypass -File setup_backup_scheduler.ps1
   ```

2. **Verify the task was created**:
   ```powershell
   Get-ScheduledTask -TaskName "ISSC_AutoBackup"
   ```

3. **Test manual backup**:
   ```powershell
   cd issc
   python manage.py auto_backup
   ```

### For Ubuntu 24.04 Linux Server

1. **Make the script executable**:
   ```bash
   cd /var/www/issc  # or your project path
   chmod +x setup_backup_scheduler_linux.sh
   ```

2. **Run the setup script** (with sudo):
   ```bash
   sudo ./setup_backup_scheduler_linux.sh
   ```

3. **Set timezone to Asia/Manila** (if not already set):
   ```bash
   sudo timedatectl set-timezone Asia/Manila
   timedatectl  # Verify
   ```

4. **Verify cron job**:
   ```bash
   crontab -l
   ```

5. **Test manual backup**:
   ```bash
   cd /var/www/issc/issc
   /var/www/issc/venv/bin/python manage.py auto_backup
   ```

6. **View backup logs**:
   ```bash
   tail -f /var/log/issc_backup.log
   ```

## Using the Backup System

### Accessing the Backup Page

1. Log in as an **Admin** user
2. Navigate to the sidebar menu
3. Click on **"Backup"** (appears after Live Feed)

### Creating Manual Backups

1. Go to the Backup page
2. Click the **"Create Backup Now"** button
3. Wait for the backup to complete (usually 5-30 seconds)
4. The page will refresh and show the new backup in the table

### Downloading Backups

1. Find the backup you want in the table
2. Click the green **"Download"** button
3. The SQL file will download to your browser's download folder

### Deleting Backups

1. Find the backup you want to delete
2. Click the red **"Delete"** button
3. Confirm the deletion
4. The backup will be removed from the server

### Understanding Backup Types

- **🤖 Automatic** - Created by the scheduled task at 00:00 daily
- **👆 Manual** - Created by clicking the "Create Backup Now" button

## Backup File Format

Backups are saved as SQL files with the following naming convention:

```
issc_backup_[type]_[timestamp].sql
```

Examples:
- `issc_backup_auto_20241209_000000.sql` - Automatic backup
- `issc_backup_manual_20241209_143022.sql` - Manual backup

## Backup Storage Location

- **Directory**: `ISSC-Django-main/backups/`
- **Full Path (Windows)**: `C:\Users\USER\Downloads\ISSC-Django-main\backups\`
- **Full Path (Linux)**: `/var/www/issc/backups/`

The directory is automatically created if it doesn't exist.

## Database Support

### MySQL Databases
- Uses `mysqldump` command
- Requires MySQL client tools to be installed
- **Windows**: Install MySQL Server or MySQL Workbench
- **Linux**: `sudo apt install mysql-client`

### SQLite Databases
- Uses simple file copy
- No additional tools required
- Works out of the box

## Automatic Cleanup

The automatic backup system includes cleanup functionality:

- **Retention Period**: 30 days (configurable)
- **What Gets Cleaned**: Only automatic backups
- **Manual Backups**: Never auto-deleted (must delete manually)
- **Runs**: Every time the automatic backup command runs

To change retention period, edit the scheduler scripts:
```bash
# Change --keep-days value
python manage.py auto_backup --cleanup --keep-days 60
```

## Restoring from Backup

### For MySQL:

**Windows:**
```powershell
mysql -u issc_user -p issc_db < path\to\backup\issc_backup_auto_20241209_000000.sql
```

**Linux:**
```bash
mysql -u issc_user -p issc_db < /var/www/issc/backups/issc_backup_auto_20241209_000000.sql
```

### For SQLite:

**Windows:**
```powershell
copy path\to\backup\issc_backup_auto_20241209_000000.sql issc\db.sqlite3
```

**Linux:**
```bash
cp /var/www/issc/backups/issc_backup_auto_20241209_000000.sql /var/www/issc/issc/db.sqlite3
```

## Troubleshooting

### Issue: "mysqldump command not found"

**Windows Solution:**
1. Install MySQL Server or MySQL Workbench
2. Add MySQL bin directory to PATH:
   - Default: `C:\Program Files\MySQL\MySQL Server 8.0\bin`
3. Restart terminal/PowerShell

**Linux Solution:**
```bash
sudo apt install mysql-client
```

### Issue: Permission denied when creating backup

**Windows Solution:**
- Run PowerShell as Administrator
- Check folder permissions on `backups/` directory

**Linux Solution:**
```bash
sudo chown -R www-data:www-data /var/www/issc/backups
sudo chmod -R 755 /var/www/issc/backups
```

### Issue: Scheduled task not running

**Windows:**
1. Open Task Scheduler (`taskschd.msc`)
2. Find "ISSC_AutoBackup" task
3. Right-click → Properties → Check:
   - Trigger is set to Daily at 00:00
   - Action has correct Python path
   - "Run whether user is logged on or not" is NOT checked (or enter password)

**Linux:**
1. Check cron logs: `sudo grep CRON /var/log/syslog`
2. Verify cron job: `crontab -l`
3. Check script permissions: `ls -la /usr/local/bin/issc_auto_backup.sh`

### Issue: Wrong timezone

**Windows:**
- Check: `Get-TimeZone`
- Set: `Set-TimeZone -Id "Singapore Standard Time"` (Manila uses this)

**Linux:**
- Check: `timedatectl`
- Set: `sudo timedatectl set-timezone Asia/Manila`

## Security Considerations

1. **Backup Directory Protection**:
   - Backups are stored outside the web root
   - Not directly accessible via URL
   - Download only through authenticated admin routes

2. **Access Control**:
   - Only admin users can access backup page
   - All backup operations require admin privileges
   - CSRF protection on all POST requests

3. **File Path Validation**:
   - All file operations validate paths are within backup directory
   - Prevents directory traversal attacks

4. **Database Credentials**:
   - Stored in environment variables (.env file)
   - Never exposed in backup filenames
   - .env file should never be committed to git

## Monitoring & Logs

### Windows
- Task Scheduler logs: Task Scheduler → Task History
- Backup output: Check Windows Event Viewer

### Linux
- Backup logs: `/var/log/issc_backup.log`
- View live: `tail -f /var/log/issc_backup.log`
- Cron logs: `sudo grep CRON /var/log/syslog`

## Performance Notes

- **Backup Duration**: Depends on database size (usually 5-30 seconds)
- **Disk Space**: Each backup is approximately the size of your database
- **Impact**: Minimal impact on running system
- **Automatic Cleanup**: Keeps disk usage under control

## Maintenance

### Weekly Tasks
1. Check backup logs for errors
2. Verify backups are being created
3. Test downloading a backup

### Monthly Tasks
1. Test restoring a backup to a test database
2. Review disk space usage
3. Adjust retention period if needed

### Quarterly Tasks
1. Archive important backups to external storage
2. Document any backup-related incidents
3. Review and update backup procedures

## Support

If you encounter issues:

1. **Check logs first**:
   - Windows: Task Scheduler History
   - Linux: `/var/log/issc_backup.log`

2. **Verify setup**:
   - Database credentials in .env
   - MySQL client tools installed
   - Correct timezone set

3. **Test manually**:
   ```bash
   python manage.py auto_backup
   ```

4. **Review this documentation** for troubleshooting steps

## Summary

You now have a complete, production-ready backup system that:

✅ Runs automatically every day at midnight (Asia/Manila time)
✅ Allows on-demand manual backups
✅ Provides a beautiful UI for backup management
✅ Works on Windows and Linux
✅ Includes automatic cleanup
✅ Supports both MySQL and SQLite
✅ Is secure and follows best practices

The backup system is fully functional and requires minimal maintenance. Just set up the scheduler once, and it will run reliably every day!
