#!/usr/bin/env python3
"""
Fix MySQL authentication for Django on production server
"""

import subprocess
import sys

def run_ssh_command(command):
    """Run command on remote server"""
    full_cmd = f'ssh root@72.62.66.193 "{command}"'
    print(f"Running: {command}")
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"Errors: {result.stderr}")
    return result.returncode == 0

def main():
    print("=" * 60)
    print("MySQL Authentication Fix for Django")
    print("=" * 60)
    
    # Check current authentication plugin
    print("\n1. Checking current MySQL root user authentication...")
    sql_check = "SELECT user, host, plugin FROM mysql.user WHERE user='root';"
    run_ssh_command(f"mysql -u root -p'Issc@2024' -e \"{sql_check}\"")
    
    # Create dedicated Django user with mysql_native_password
    print("\n2. Creating dedicated Django database user...")
    sql_commands = """
CREATE USER IF NOT EXISTS 'issc_user'@'localhost' IDENTIFIED BY 'Issc@2024';
GRANT ALL PRIVILEGES ON issc.* TO 'issc_user'@'localhost';
FLUSH PRIVILEGES;
SELECT user, host, plugin FROM mysql.user WHERE user='issc_user';
"""
    
    # Write SQL to temp file and execute
    run_ssh_command(f"cat > /tmp/fix_mysql.sql << 'EOF'\n{sql_commands}\nEOF")
    run_ssh_command("mysql -u root -p'Issc@2024' < /tmp/fix_mysql.sql")
    
    # Update .env file
    print("\n3. Updating .env file with new database user...")
    run_ssh_command("cd /var/www/issc && sed -i 's/DB_USER=root/DB_USER=issc_user/' .env")
    
    # Verify .env update
    print("\n4. Verifying .env file update...")
    run_ssh_command("cat /var/www/issc/.env | grep DB_USER")
    
    # Restart Gunicorn
    print("\n5. Restarting Gunicorn...")
    run_ssh_command("systemctl restart gunicorn")
    run_ssh_command("systemctl status gunicorn --no-pager -l")
    
    print("\n" + "=" * 60)
    print("MySQL authentication fix completed!")
    print("Test the website at: https://issc.study")
    print("=" * 60)

if __name__ == "__main__":
    main()
