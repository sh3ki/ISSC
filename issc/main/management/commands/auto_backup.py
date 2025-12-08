"""
Management command for automatic database backup
Run this command daily at 00:00 Asia/Manila time
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
import sys
import os

# Add the views directory to the path so we can import backup_view
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'views'))

from main.views.backup_view import create_backup, get_manila_time

class Command(BaseCommand):
    help = 'Create an automatic database backup'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Remove backups older than 30 days',
        )
        parser.add_argument(
            '--keep-days',
            type=int,
            default=30,
            help='Number of days to keep automatic backups (default: 30)',
        )

    def handle(self, *args, **options):
        manila_time = get_manila_time()
        self.stdout.write(
            self.style.SUCCESS(f'Starting automatic backup at {manila_time.strftime("%Y-%m-%d %H:%M:%S")} (Asia/Manila)')
        )

        # Create backup
        success, message, backup_info = create_backup('auto')

        if success:
            self.stdout.write(
                self.style.SUCCESS(f'[SUCCESS] Backup created successfully: {backup_info["filename"]}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'  Size: {backup_info["size"] / (1024*1024):.2f} MB')
            )
            self.stdout.write(
                self.style.SUCCESS(f'  Location: {backup_info["filepath"]}')
            )

            # Cleanup old backups if requested
            if options['cleanup']:
                self.cleanup_old_backups(options['keep_days'])
        else:
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Backup failed: {message}')
            )
            sys.exit(1)

    def cleanup_old_backups(self, keep_days):
        """Remove automatic backups older than specified days"""
        from main.views.backup_view import BACKUP_DIR, get_backup_list
        from datetime import timedelta
        import os

        self.stdout.write('\nCleaning up old automatic backups...')
        
        backups = get_backup_list()
        cutoff_date = timezone.now() - timedelta(days=keep_days)
        deleted_count = 0
        freed_space = 0

        for backup in backups:
            # Only delete automatic backups
            if backup['type'] == 'automatic' and backup['created'] < cutoff_date:
                try:
                    file_size = backup['size']
                    os.remove(backup['filepath'])
                    deleted_count += 1
                    freed_space += file_size
                    self.stdout.write(
                        self.style.WARNING(f'  Deleted: {backup["filename"]} (created {backup["created"].strftime("%Y-%m-%d")})')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  Failed to delete {backup["filename"]}: {str(e)}')
                    )

        if deleted_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\n[SUCCESS] Cleanup complete: {deleted_count} files deleted, {freed_space / (1024*1024):.2f} MB freed')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\n[SUCCESS] No old backups to clean up')
            )
