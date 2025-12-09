import os
import subprocess
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import JsonResponse, FileResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages
import json
import platform
from pathlib import Path
import pytz

# Create backups directory if it doesn't exist
BACKUP_DIR = os.path.join(settings.BASE_DIR, 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)

def get_manila_time():
    """Get current time in Asia/Manila timezone"""
    manila_tz = pytz.timezone('Asia/Manila')
    return datetime.now(manila_tz)

def get_database_config():
    """Extract database configuration from settings"""
    db_config = settings.DATABASES['default']
    
    if db_config['ENGINE'] == 'django.db.backends.mysql':
        return {
            'type': 'mysql',
            'name': db_config['NAME'],
            'user': db_config['USER'],
            'password': db_config['PASSWORD'],
            'host': db_config.get('HOST', 'localhost'),
            'port': db_config.get('PORT', '3306'),
        }
    elif db_config['ENGINE'] == 'django.db.backends.sqlite3':
        return {
            'type': 'sqlite',
            'name': db_config['NAME'],
        }
    return None

def create_mysql_backup(db_config, backup_file):
    """Create MySQL database backup"""
    system = platform.system()
    
    if system == 'Windows':
        # Windows command
        cmd = [
            'mysqldump',
            '-h', db_config['host'],
            '-P', str(db_config['port']),
            '-u', db_config['user'],
            f'-p{db_config["password"]}',
            db_config['name']
        ]
    else:
        # Linux command
        cmd = [
            'mysqldump',
            '-h', db_config['host'],
            '-P', str(db_config['port']),
            '-u', db_config['user'],
            f'--password={db_config["password"]}',
            db_config['name']
        ]
    
    try:
        with open(backup_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            
        if result.returncode == 0:
            return True, "Backup created successfully"
        else:
            return False, result.stderr
    except FileNotFoundError:
        return False, "mysqldump command not found. Please ensure MySQL client is installed."
    except Exception as e:
        return False, str(e)

def create_sqlite_backup(db_config, backup_file):
    """Create SQLite database backup"""
    try:
        import shutil
        shutil.copy2(db_config['name'], backup_file)
        return True, "Backup created successfully"
    except Exception as e:
        return False, str(e)

def create_backup(backup_type='manual'):
    """Create a database backup"""
    db_config = get_database_config()
    
    if not db_config:
        return False, "Unsupported database type", None
    
    # Generate filename with timestamp
    manila_time = get_manila_time()
    timestamp = manila_time.strftime('%Y%m%d_%H%M%S')
    filename = f"issc_backup_{backup_type}_{timestamp}.sql"
    backup_file = os.path.join(BACKUP_DIR, filename)
    
    # Create backup based on database type
    if db_config['type'] == 'mysql':
        success, message = create_mysql_backup(db_config, backup_file)
    elif db_config['type'] == 'sqlite':
        success, message = create_sqlite_backup(db_config, backup_file)
    else:
        return False, "Unsupported database type", None
    
    if success:
        # Get file size
        file_size = os.path.getsize(backup_file)
        return True, message, {
            'filename': filename,
            'filepath': backup_file,
            'size': file_size,
            'timestamp': manila_time.isoformat(),
            'type': backup_type
        }
    else:
        return False, message, None

def get_backup_list():
    """Get list of all backup files"""
    backups = []
    
    if not os.path.exists(BACKUP_DIR):
        return backups
    
    for filename in os.listdir(BACKUP_DIR):
        if filename.endswith('.sql'):
            filepath = os.path.join(BACKUP_DIR, filename)
            file_stats = os.stat(filepath)
            
            # Parse backup type from filename
            backup_type = 'manual'
            if '_auto_' in filename:
                backup_type = 'automatic'
            elif '_manual_' in filename:
                backup_type = 'manual'
            
            backups.append({
                'filename': filename,
                'filepath': filepath,
                'size': file_stats.st_size,
                'created': datetime.fromtimestamp(file_stats.st_ctime),
                'type': backup_type
            })
    
    # Sort by creation time, newest first
    backups.sort(key=lambda x: x['created'], reverse=True)
    
    return backups

@login_required
def backup_page(request):
    """Display backup management page"""
    # Check if user is admin
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    backups = get_backup_list()
    manila_time = get_manila_time()
    
    # Get user role for navigation menu
    from main.models import AccountRegistration
    try:
        user_account = AccountRegistration.objects.get(id_number=request.user.id_number)
        user_role = user_account.privilege
    except:
        user_role = 'admin'  # Default to admin if user is staff
    
    context = {
        'backups': backups,
        'current_time': manila_time,
        'backup_schedule': '00:00 (Asia/Manila)',
        'total_backups': len(backups),
        'total_size': sum(b['size'] for b in backups),
        'user_role': user_role,
    }
    
    return render(request, 'backup.html', context)

@login_required
def create_manual_backup(request):
    """Create a manual backup via AJAX"""
    # Check if user is admin
    if not request.user.is_staff and not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Access denied'}, status=403)
    
    if request.method == 'POST':
        success, message, backup_info = create_backup('manual')
        
        if success:
            return JsonResponse({
                'success': True,
                'message': message,
                'backup': {
                    'filename': backup_info['filename'],
                    'size': backup_info['size'],
                    'timestamp': backup_info['timestamp'],
                    'type': backup_info['type']
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'message': message
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)

@login_required
def download_backup(request, filename):
    """Download a backup file"""
    # Check if user is admin
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('backup_page')
    
    filepath = os.path.join(BACKUP_DIR, filename)
    
    if not os.path.exists(filepath):
        messages.error(request, 'Backup file not found.')
        return redirect('backup_page')
    
    # Security check: ensure the file is within BACKUP_DIR
    if not os.path.abspath(filepath).startswith(os.path.abspath(BACKUP_DIR)):
        messages.error(request, 'Invalid file path.')
        return redirect('backup_page')
    
    try:
        response = FileResponse(open(filepath, 'rb'), content_type='application/sql')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        messages.error(request, f'Error downloading file: {str(e)}')
        return redirect('backup_page')

@login_required
def delete_backup(request, filename):
    """Delete a backup file"""
    # Check if user is admin
    if not request.user.is_staff and not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Access denied'}, status=403)
    
    if request.method == 'POST':
        filepath = os.path.join(BACKUP_DIR, filename)
        
        if not os.path.exists(filepath):
            return JsonResponse({'success': False, 'message': 'Backup file not found'}, status=404)
        
        # Security check: ensure the file is within BACKUP_DIR
        if not os.path.abspath(filepath).startswith(os.path.abspath(BACKUP_DIR)):
            return JsonResponse({'success': False, 'message': 'Invalid file path'}, status=400)
        
        try:
            os.remove(filepath)
            return JsonResponse({'success': True, 'message': 'Backup deleted successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)
