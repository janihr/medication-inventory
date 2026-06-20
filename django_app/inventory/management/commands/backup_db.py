import os
import subprocess
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone


class Command(BaseCommand):
    help = 'Create a PostgreSQL database backup (pg_dump)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output', '-o',
            type=str,
            default='',
            help='Output file path. Default: <backup_dir>/backup_YYYYMMDD_HHMMSS.sql'
        )
        parser.add_argument(
            '--compress', '-c',
            action='store_true',
            help='Use gzip compression (.sql.gz)'
        )

    def handle(self, *args, **options):
        from inventory.models import BackupSettings

        backup_settings = BackupSettings.get_settings()
        backup_dir = Path(backup_settings.backup_dir)

        # Ensure backup directory exists
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Determine output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if options['output']:
            output_file = Path(options['output'])
        else:
            ext = '.sql.gz' if options['compress'] else '.sql'
            output_file = backup_dir / f'backup_{timestamp}{ext}'

        # Database settings
        db_settings = settings.DATABASES['default']
        db_name = db_settings['NAME']
        db_user = db_settings['USER']
        db_password = db_settings['PASSWORD']
        db_host = db_settings.get('HOST', 'db')
        db_port = db_settings.get('PORT', '5432')

        # Build pg_dump command
        env = os.environ.copy()
        env['PGPASSWORD'] = db_password

        cmd = [
            'pg_dump',
            '-h', db_host,
            '-p', str(db_port),
            '-U', db_user,
            '-d', db_name,
            '--no-owner',
            '--no-acl',
        ]

        self.stdout.write(f'Creating backup: {output_file}')

        try:
            if options['compress']:
                # Pipe through gzip
                with open(output_file, 'wb') as f:
                    pg_dump_proc = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
                    )
                    gzip_proc = subprocess.Popen(
                        ['gzip'], stdin=pg_dump_proc.stdout, stdout=f, stderr=subprocess.PIPE
                    )
                    pg_dump_proc.stdout.close()
                    gzip_out, gzip_err = gzip_proc.communicate()
                    pg_dump_proc.wait()

                    if pg_dump_proc.returncode != 0:
                        _, pg_err = pg_dump_proc.communicate()
                        raise subprocess.CalledProcessError(
                            pg_dump_proc.returncode, cmd, stderr=pg_err
                        )
            else:
                with open(output_file, 'w') as f:
                    result = subprocess.run(
                        cmd, stdout=f, stderr=subprocess.PIPE, env=env, check=True
                    )

            # Get file size
            file_size = output_file.stat().st_size
            size_str = self._format_size(file_size)

            # Update backup settings
            backup_settings.last_backup_at = timezone.now()
            backup_settings.last_backup_file = str(output_file)
            backup_settings.last_backup_status = 'success'
            backup_settings.save()

            self.stdout.write(self.style.SUCCESS(
                f'Backup created successfully: {output_file} ({size_str})'
            ))

            # Cleanup old backups
            self._cleanup_old_backups(backup_dir, backup_settings.retention_days)

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            backup_settings.last_backup_status = f'failed: {error_msg[:200]}'
            backup_settings.save()
            raise CommandError(f'pg_dump failed: {error_msg}')

        except Exception as e:
            backup_settings.last_backup_status = f'failed: {str(e)[:200]}'
            backup_settings.save()
            raise CommandError(f'Backup failed: {e}')

    def _cleanup_old_backups(self, backup_dir, retention_days):
        """Remove backups older than retention_days."""
        if retention_days == 0:
            return

        cutoff = timezone.now() - timezone.timedelta(days=retention_days)
        removed_count = 0

        for f in backup_dir.glob('backup_*'):
            if f.is_file():
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.get_current_timezone())
                if mtime < cutoff:
                    f.unlink()
                    removed_count += 1

        if removed_count > 0:
            self.stdout.write(f'Cleaned up {removed_count} old backup(s).')

    def _format_size(self, size_bytes):
        """Format bytes to human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f'{size_bytes:.1f} {unit}'
            size_bytes /= 1024
        return f'{size_bytes:.1f} TB'