#!/usr/bin/env python
"""
Test script to verify mysqldump functionality
"""
import subprocess
import os
import sys

# Add the project path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'issc'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'issc.settings')
import django
django.setup()

from django.conf import settings

def test_mysqldump():
    """Test mysqldump command"""
    print("=" * 60)
    print("MySQL Backup Test")
    print("=" * 60)
    
    db_config = settings.DATABASES['default']
    
    print(f"\nDatabase Configuration:")
    print(f"  Engine: {db_config['ENGINE']}")
    print(f"  Name: {db_config['NAME']}")
    print(f"  User: {db_config['USER']}")
    print(f"  Host: {db_config.get('HOST', 'localhost')}")
    print(f"  Port: {db_config.get('PORT', '3306')}")
    print(f"  Password: {'*' * len(db_config.get('PASSWORD', '')) if db_config.get('PASSWORD') else '(empty)'}")
    
    # Build mysqldump command
    cmd = [
        'mysqldump',
        '-h', db_config.get('HOST', 'localhost'),
        '-P', str(db_config.get('PORT', '3306')),
        '-u', db_config['USER'],
        '--single-transaction',
        '--routines',
        '--triggers',
        '--events',
        db_config['NAME']
    ]
    
    if db_config.get('PASSWORD'):
        cmd.insert(6, f'-p{db_config["PASSWORD"]}')
    
    print(f"\nCommand (password hidden):")
    safe_cmd = [c if not c.startswith('-p') else '-p***' for c in cmd]
    print(f"  {' '.join(safe_cmd)}")
    
    # Test mysqldump
    print(f"\nTesting mysqldump...")
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=30
        )
        
        print(f"\nReturn Code: {result.returncode}")
        
        if result.stderr:
            print(f"\nStderr Output:")
            print(result.stderr)
        
        if result.stdout:
            output_size = len(result.stdout)
            lines = result.stdout.split('\n')
            print(f"\nStdout Summary:")
            print(f"  Size: {output_size} bytes")
            print(f"  Lines: {len(lines)}")
            print(f"\nFirst 10 lines:")
            for i, line in enumerate(lines[:10], 1):
                print(f"  {i}: {line[:80]}")
            
            if output_size > 0:
                print(f"\n✅ SUCCESS: mysqldump produced output ({output_size} bytes)")
                
                # Try to save to file
                test_file = 'test_backup.sql'
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)
                
                file_size = os.path.getsize(test_file)
                print(f"✅ Test backup file created: {test_file} ({file_size} bytes)")
                
                return True
            else:
                print(f"\n❌ ERROR: mysqldump produced empty output")
                return False
        else:
            print(f"\n❌ ERROR: No stdout output from mysqldump")
            return False
            
    except FileNotFoundError:
        print(f"\n❌ ERROR: mysqldump command not found")
        print("Please ensure MySQL client tools are installed and added to PATH")
        return False
    except subprocess.TimeoutExpired:
        print(f"\n❌ ERROR: mysqldump timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False

if __name__ == '__main__':
    success = test_mysqldump()
    print("\n" + "=" * 60)
    if success:
        print("✅ Test completed successfully")
    else:
        print("❌ Test failed - check the errors above")
    print("=" * 60)
    sys.exit(0 if success else 1)
