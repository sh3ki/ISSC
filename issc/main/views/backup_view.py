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
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    # Set secure permissions on Linux/Ubuntu (rwx for owner only)
    if platform.system() != 'Windows':
        os.chmod(BACKUP_DIR, 0o700)

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
    
    # Base command without password
    cmd = [
        'mysqldump',
        '-h', db_config['host'],
        '-P', str(db_config['port']),
        '-u', db_config['user'],
        '--single-transaction',
        '--routines',
        '--triggers',
        '--events',
        '--skip-comments',
        '--add-drop-table',
        db_config['name']
    ]
    
    # Prepare environment variables for password (more secure for Linux)
    env = os.environ.copy()
    
    if system == 'Windows':
        # Windows: Add password directly to command if provided
        if db_config['password']:
            cmd.insert(4, f'-p{db_config["password"]}')
    else:
        # Linux/Ubuntu: Use environment variable for password (more secure)
        if db_config['password']:
            env['MYSQL_PWD'] = db_config['password']
    
    try:
        # Execute mysqldump and capture output
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            encoding='utf-8',
            errors='replace',
            env=env
        )
        
        # Check for errors (ignore password warning on stderr)
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            # Filter out password warning which is common and not an actual error
            if 'mysql: [Warning] Using a password on the command line' not in error_msg:
                print(f"mysqldump error: {error_msg}")
                return False, f"mysqldump failed: {error_msg}"
        
        # Check if output is not empty
        if not result.stdout or len(result.stdout.strip()) == 0:
            return False, "mysqldump produced empty output. Check database connection and credentials."
        
        # Write the SQL dump to file with proper permissions on Linux
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
        
        # Set file permissions on Linux (read/write for owner only)
        if system != 'Windows':
            os.chmod(backup_file, 0o600)
        
        # Verify the file was created and has content
        if os.path.exists(backup_file):
            file_size = os.path.getsize(backup_file)
            if file_size > 0:
                print(f"Backup created successfully: {backup_file} ({file_size} bytes)")
                return True, "Backup created successfully"
            else:
                return False, "Backup file is empty"
        else:
            return False, "Backup file was not created"
            
    except FileNotFoundError:
        system_hint = "apt install mysql-client" if system == 'Linux' else "Install MySQL client tools"
        return False, f"mysqldump command not found. Please install MySQL client: {system_hint}"
    except Exception as e:
        print(f"Backup exception: {str(e)}")
        return False, f"Error creating backup: {str(e)}"

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
    
    print(f"Creating {backup_type} backup for {db_config['type']} database: {db_config.get('name', 'unknown')}")
    
    # Generate filename with timestamp
    manila_time = get_manila_time()
    timestamp = manila_time.strftime('%Y%m%d_%H%M%S')
    filename = f"issc_backup_{backup_type}_{timestamp}.sql"
    backup_file = os.path.join(BACKUP_DIR, filename)
    
    print(f"Backup file path: {backup_file}")
    
    # Create backup based on database type
    if db_config['type'] == 'mysql':
        success, message = create_mysql_backup(db_config, backup_file)
    elif db_config['type'] == 'sqlite':
        success, message = create_sqlite_backup(db_config, backup_file)
    else:
        return False, "Unsupported database type", None
    
    if success:
        # Verify file exists and has content
        if os.path.exists(backup_file):
            file_size = os.path.getsize(backup_file)
            if file_size > 0:
                print(f"Backup successful! File: {filename}, Size: {file_size} bytes")
                return True, message, {
                    'filename': filename,
                    'filepath': backup_file,
                    'size': file_size,
                    'timestamp': manila_time.isoformat(),
                    'type': backup_type
                }
            else:
                print("Error: Backup file is empty")
                # Delete empty file
                try:
                    os.remove(backup_file)
                except:
                    pass
                return False, "Backup file is empty. Check database connection.", None
        else:
            print("Error: Backup file was not created")
            return False, "Backup file was not created", None
    else:
        print(f"Backup failed: {message}")
        # Clean up any partial file
        if os.path.exists(backup_file):
            try:
                os.remove(backup_file)
            except:
                pass
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
