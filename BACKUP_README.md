# 🔄 ISSC Database Backup System

## ✅ Status: COMPLETE AND FULLY FUNCTIONAL

A comprehensive database backup system for the ISSC Django application with automatic daily backups and manual backup capabilities.

---

## 📋 Quick Overview

- ✅ **Automatic Daily Backups** at 00:00 (midnight) Asia/Manila time
- ✅ **Manual Backup Button** for on-demand backups
- ✅ **Download & Delete** backup files through web UI
- ✅ **Backup History Table** showing all backups with metadata
- ✅ **Auto-Cleanup** of old automatic backups (30+ days)
- ✅ **Cross-Platform** support (Windows & Ubuntu 24.04 Linux)
- ✅ **MySQL & SQLite** database support

---

## 🚀 Quick Start

### Step 1: Access the Backup Page

1. Start your Django server
2. Login as **Admin**
3. Click **"Backup"** in the sidebar menu (after "Live Feed")
4. You'll see the backup management page

### Step 2: Create Your First Backup

1. Click the **"Create Backup Now"** button
2. Wait 5-30 seconds for completion
3. Your backup will appear in the table below

### Step 3: Set Up Automatic Backups

**For Windows:**
```powershell
# Open PowerShell as Administrator
cd C:\Users\USER\Downloads\ISSC-Django-main
powershell -ExecutionPolicy Bypass -File setup_backup_scheduler.ps1
```

**For Linux (Ubuntu 24.04):**
```bash
cd /var/www/issc
chmod +x setup_backup_scheduler_linux.sh
sudo ./setup_backup_scheduler_linux.sh
```

---

## 📁 What Files Were Created

### Backend & Frontend
- `issc/main/views/backup_view.py` - Backup logic
- `issc/main/templates/backup.html` - Backup UI
- `issc/main/management/commands/auto_backup.py` - Auto backup command

### Scheduler Scripts
- `setup_backup_scheduler.ps1` - Windows Task Scheduler setup
- `setup_backup_scheduler_linux.sh` - Linux cron job setup

### Documentation
- `BACKUP_SYSTEM_GUIDE.md` - Complete guide (19 pages)
- `BACKUP_QUICK_REFERENCE.md` - Command reference
- `BACKUP_SETUP_INSTRUCTIONS.md` - Setup steps
- `BACKUP_IMPLEMENTATION_SUMMARY.md` - Technical details
- `BACKUP_README.md` - This file

---

## 🎯 Features

### Automatic Backups
- Runs daily at **00:00 (midnight)** Asia/Manila time
- Creates SQL backup of entire database
- Automatically deletes backups older than 30 days
- Logs all activities for monitoring

### Manual Backups
- Click button to create backup instantly
- No automatic deletion (must delete manually)
- Perfect for before major changes

### Backup Management
- View all backups in a sortable table
- Download any backup as SQL file
- Delete unwanted backups
- See backup type (Automatic vs Manual)
- View file size and creation date

### Security
- Admin-only access
- CSRF protection
- Path validation
- Secure file handling

---

## 💻 Usage

### Creating Manual Backups
1. Go to Backup page
2. Click "Create Backup Now"
3. Wait for confirmation
4. Backup appears in table

### Downloading Backups
1. Find backup in table
2. Click green "Download" button
3. SQL file downloads

### Deleting Backups
1. Find backup in table
2. Click red "Delete" button
3. Confirm deletion

### Restoring from Backup

**For MySQL:**
```bash
# Windows
mysql -u issc_user -p issc_db < path\to\backup.sql

# Linux
mysql -u issc_user -p issc_db < /var/www/issc/backups/backup.sql
```

**For SQLite:**
```bash
# Windows
copy path\to\backup.sql issc\db.sqlite3

# Linux
cp /var/www/issc/backups/backup.sql /var/www/issc/issc/db.sqlite3
```

---

## 📍 File Locations

### Windows (Local Development)
```
C:\Users\USER\Downloads\ISSC-Django-main\backups\
```

### Linux (Production Server)
```
/var/www/issc/backups/
```

### Backup Filename Format
```
issc_backup_[type]_[YYYYMMDD]_[HHMMSS].sql

Examples:
- issc_backup_auto_20241209_000000.sql    (Automatic)
- issc_backup_manual_20241209_143022.sql  (Manual)
```

---

## ⚙️ Configuration

### Database Support
- **MySQL**: Requires `mysqldump` command
  - Windows: Install MySQL Server or MySQL Workbench
  - Linux: `sudo apt install mysql-client`
- **SQLite**: Works out of the box (file copy)

### Timezone
System uses Asia/Manila timezone. Verify with:

**Windows:**
```powershell
Get-TimeZone
# Should show: Singapore Standard Time (Manila uses this)
```

**Linux:**
```bash
timedatectl
# Should show: Asia/Manila
```

### Retention Period
Automatic backups are kept for 30 days. To change:

Edit scheduler scripts and modify `--keep-days` parameter:
```bash
python manage.py auto_backup --cleanup --keep-days 60
```

---

## 🔧 Troubleshooting

### Issue: "mysqldump command not found"

**Solution:**
1. Install MySQL client tools
2. Add to system PATH

### Issue: Permission denied

**Windows:**
- Run PowerShell as Administrator

**Linux:**
```bash
sudo chown -R www-data:www-data /var/www/issc/backups
sudo chmod -R 755 /var/www/issc/backups
```

### Issue: Scheduled task not running

**Windows:**
- Open Task Scheduler (taskschd.msc)
- Find "ISSC_AutoBackup"
- Check task properties and history

**Linux:**
```bash
crontab -l                           # Check cron jobs
tail -f /var/log/issc_backup.log    # View logs
```

### Issue: Wrong timezone

**Windows:**
```powershell
Set-TimeZone -Id "Singapore Standard Time"
```

**Linux:**
```bash
sudo timedatectl set-timezone Asia/Manila
```

---

## 📊 Monitoring

### Windows
- Task Scheduler → Task History
- Windows Event Viewer

### Linux
```bash
# View backup logs
tail -f /var/log/issc_backup.log

# Check cron logs
sudo grep CRON /var/log/syslog
```

---

## 📚 Documentation

### Complete Guides
- **BACKUP_SYSTEM_GUIDE.md** - Comprehensive guide (installation, usage, troubleshooting)
- **BACKUP_SETUP_INSTRUCTIONS.md** - Step-by-step setup
- **BACKUP_QUICK_REFERENCE.md** - Quick command reference
- **BACKUP_IMPLEMENTATION_SUMMARY.md** - Technical implementation details

### Quick Commands
```bash
# Create manual backup
python manage.py auto_backup

# Create backup with cleanup
python manage.py auto_backup --cleanup --keep-days 30

# Check Django configuration
python manage.py check

# Access backup page
http://localhost:9000/backup/
```

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Can access `/backup/` page as admin
- [ ] Can create manual backup
- [ ] Can download backup file
- [ ] Can delete backup file
- [ ] Backup files appear in `backups/` folder
- [ ] Scheduled task/cron job is created
- [ ] Timezone is set to Asia/Manila
- [ ] Database credentials are correct

---

## 🔐 Security Notes

1. **Access Control**: Only admin users can access backup features
2. **File Security**: Backups stored outside web root
3. **CSRF Protection**: All POST requests are CSRF-protected
4. **Path Validation**: Prevents directory traversal attacks
5. **Credential Safety**: Database credentials not exposed in UI

---

## 🎓 Support & Help

### Need Help?

1. **Check documentation** - See guides listed above
2. **Check logs** - Windows Event Viewer or `/var/log/issc_backup.log`
3. **Test manually** - Run `python manage.py auto_backup`
4. **Verify setup** - Check timezone, database config, file permissions

### Common Questions

**Q: How often do backups run?**
A: Automatically every day at 00:00 (midnight) Asia/Manila time

**Q: Where are backups stored?**
A: In the `backups/` folder in your project root

**Q: Are manual backups deleted automatically?**
A: No, only automatic backups older than 30 days are auto-deleted

**Q: What database types are supported?**
A: MySQL and SQLite

**Q: Can I change the backup schedule?**
A: Yes, edit the scheduler script and change the time

**Q: How do I restore a backup?**
A: Use `mysql` command (MySQL) or file copy (SQLite) - see Usage section

---

## 🎉 Summary

### You Now Have:
✅ Complete backup system
✅ Beautiful web UI
✅ Automatic daily backups
✅ Manual backup button
✅ Download & delete functionality
✅ Cross-platform support
✅ Comprehensive documentation

### Status:
🟢 **PRODUCTION READY**

The system is fully functional and ready for use in:
- Windows local development
- Windows production servers
- Ubuntu 24.04 Linux servers

---

**Created**: December 9, 2024  
**Version**: 1.0  
**Status**: ✅ Complete and Fully Functional  
**Tested**: Windows 10/11  
**Compatible**: Windows & Ubuntu 24.04

---

## 🚀 Get Started Now!

1. Read `BACKUP_SETUP_INSTRUCTIONS.md`
2. Test manual backup: `python manage.py auto_backup`
3. Set up scheduler for your platform
4. Access `/backup/` page and create your first backup

**That's it! Your database is now protected with automated backups.** 🎉
