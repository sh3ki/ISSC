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

def find_mysqldump():
    """Find mysqldump executable on Windows and Linux"""
    import shutil
    import glob
    system = platform.system()
    
    # Try to find in PATH first
    mysqldump_path = shutil.which('mysqldump')
    if mysqldump_path:
        return mysqldump_path
    
    if system == 'Windows':
        common_paths = [
            r'C:\laragon\bin\mysql\mysql-*\bin\mysqldump.exe',
            r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe',
            r'C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe',
            r'C:\Program Files\MySQL\MySQL Server 5.7\bin\mysqldump.exe',
            r'C:\Program Files (x86)\MySQL\MySQL Server 8.0\bin\mysqldump.exe',
            r'C:\Program Files (x86)\MySQL\MySQL Server 5.7\bin\mysqldump.exe',
            r'C:\xampp\mysql\bin\mysqldump.exe',
            r'C:\wamp64\bin\mysql\mysql8.0.*\bin\mysqldump.exe',
        ]
        for path in common_paths:
            if '*' in path:
                matches = glob.glob(path)
                if matches:
                    return matches[0]
            elif os.path.exists(path):
                return path
    else:
        # Linux: search common locations
        linux_paths = [
            '/usr/bin/mysqldump',
            '/usr/local/bin/mysqldump',
            '/usr/local/mysql/bin/mysqldump',
            '/opt/mysql/bin/mysqldump',
        ]
        for path in linux_paths:
            if os.path.exists(path):
                return path
    
    return None


def create_mysql_backup_python(db_config, backup_file):
    """
    Pure-Python MySQL backup using Django's DB connection.
    Works without mysqldump installed — generates a valid SQL dump file.
    """
    try:
        import MySQLdb
    except ImportError:
        try:
            import pymysql as MySQLdb
        except ImportError:
            return False, "Neither MySQLdb nor pymysql is available for Python-based backup."

    try:
        conn = MySQLdb.connect(
            host=db_config['host'],
            port=int(db_config['port'] or 3306),
            user=db_config['user'],
            passwd=db_config['password'],
            db=db_config['name'],
            charset='utf8mb4',
        )
        cursor = conn.cursor()

        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(f"-- ISSC Database Backup\n")
            f.write(f"-- Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
            f.write(f"-- Database: {db_config['name']}\n\n")
            f.write("SET FOREIGN_KEY_CHECKS=0;\n")
            f.write("SET SQL_MODE='NO_AUTO_VALUE_ON_ZERO';\n")
            f.write("SET NAMES utf8mb4;\n\n")

            # Get all tables
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                # Drop + Create statement
                cursor.execute(f"SHOW CREATE TABLE `{table}`")
                create_row = cursor.fetchone()
                f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                f.write(create_row[1] + ";\n\n")

                # Data rows
                cursor.execute(f"SELECT * FROM `{table}`")
                rows = cursor.fetchall()
                if rows:
                    # Column names
                    col_names = [desc[0] for desc in cursor.description]
                    cols = ', '.join(f"`{c}`" for c in col_names)
                    for row in rows:
                        values = []
                        for v in row:
                            if v is None:
                                values.append('NULL')
                            elif isinstance(v, (int, float)):
                                values.append(str(v))
                            elif isinstance(v, bytes):
                                values.append("0x" + v.hex())
                            else:
                                escaped = str(v).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")
                                values.append(f"'{escaped}'")
                        vals = ', '.join(values)
                        f.write(f"INSERT INTO `{table}` ({cols}) VALUES ({vals});\n")
                    f.write("\n")

            f.write("SET FOREIGN_KEY_CHECKS=1;\n")

        cursor.close()
        conn.close()

        # Set permissions on Linux
        if platform.system() != 'Windows':
            try:
                os.chmod(backup_file, 0o666)
            except Exception:
                pass

        file_size = os.path.getsize(backup_file)
        print(f"Python-based backup created: {backup_file} ({file_size} bytes)")
        return True, "Backup created successfully (Python-based)"

    except Exception as e:
        if os.path.exists(backup_file):
            try:
                os.remove(backup_file)
            except Exception:
                pass
        return False, f"Python backup error: {str(e)}"

def create_mysql_backup(db_config, backup_file):
    """Create MySQL database backup - works on both Windows and Linux.
    Uses mysqldump if available, otherwise falls back to pure-Python dump."""
    system = platform.system()
    
    # Find mysqldump executable
    mysqldump_cmd = find_mysqldump()
    if not mysqldump_cmd:
        print("mysqldump not found, falling back to Python-based backup...")
        return create_mysql_backup_python(db_config, backup_file)
    
    print(f"Using mysqldump: {mysqldump_cmd}")
    
    # Prepare environment variables for password (works on all systems)
    env = os.environ.copy()
    if db_config['password']:
        env['MYSQL_PWD'] = db_config['password']
    
    # Build mysqldump command (no password in command line for security)
    cmd = [
        mysqldump_cmd,
        '-h', db_config['host'],
        '-P', str(db_config['port']),
        '-u', db_config['user'],
        '--single-transaction',
        '--routines',
        '--triggers',
        '--events',
        '--add-drop-table',
        '--result-file', backup_file,  # Write directly to file
        db_config['name']
    ]
    
    try:
        print(f"Executing mysqldump command: {' '.join(cmd[:-1])} [database_name]")
        
        # Execute mysqldump
        result = subprocess.run(
            cmd, 
            stderr=subprocess.PIPE, 
            text=True,
            encoding='utf-8',
            errors='replace',
            env=env,
            timeout=300  # 5 minute timeout
        )
        
        # Check for errors
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            print(f"mysqldump error (code {result.returncode}): {error_msg}")
            
            # Clean up any partial file
            if os.path.exists(backup_file):
                try:
                    os.remove(backup_file)
                except:
                    pass
            
            return False, f"mysqldump failed: {error_msg}"
        
        # Verify the file was created and has content
        if not os.path.exists(backup_file):
            return False, "Backup file was not created by mysqldump"
        
        file_size = os.path.getsize(backup_file)
        if file_size == 0:
            os.remove(backup_file)
            return False, "mysqldump created an empty file. Check database connection and credentials."
        
        # Set secure file permissions on Linux
        if system != 'Windows':
            try:
                os.chmod(backup_file, 0o666)
            except Exception:
                pass
        
        print(f"Backup created successfully: {backup_file} ({file_size} bytes)")
        return True, "Backup created successfully"
            
    except subprocess.TimeoutExpired:
        if os.path.exists(backup_file):
            try:
                os.remove(backup_file)
            except:
                pass
        return False, "mysqldump timed out (5 minutes). Database may be too large or connection is slow."
    except Exception as e:
        print(f"Backup exception: {str(e)}")
        if os.path.exists(backup_file):
            try:
                os.remove(backup_file)
            except:
                pass
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
            # Ensure the file is writable before attempting removal
            # (handles cases where file was created by a different user/process)
            if platform.system() != 'Windows':
                try:
                    os.chmod(filepath, 0o644)
                except Exception:
                    pass
            os.remove(filepath)
            return JsonResponse({'success': True, 'message': 'Backup deleted successfully'})
        except PermissionError:
            # Last resort: use sudo rm on Linux if running user lacks write permission
            if platform.system() != 'Windows':
                try:
                    result = subprocess.run(['rm', '-f', filepath], capture_output=True, text=True)
                    if result.returncode == 0:
                        return JsonResponse({'success': True, 'message': 'Backup deleted successfully'})
                    else:
                        return JsonResponse({'success': False, 'message': f'Permission denied: {result.stderr}'}, status=500)
                except Exception as e2:
                    return JsonResponse({'success': False, 'message': str(e2)}, status=500)
            return JsonResponse({'success': False, 'message': 'Permission denied deleting backup file'}, status=500)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)
