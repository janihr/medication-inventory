from pathlib import Path
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'List available database backups'

    def handle(self, *args, **options):
        from inventory.models import BackupSettings

        settings = BackupSettings.get_settings()
        backup_dir = Path(settings.backup_dir)

        if not backup_dir.exists():
            self.stdout.write('No backup directory found.')
            return

        backups = sorted(backup_dir.glob('backup_*'), key=lambda f: f.stat().st_mtime, reverse=True)

        if not backups:
            self.stdout.write('No backups found.')
            return

        self.stdout.write(f'\nBackups in: {backup_dir}')
        self.stdout.write('-' * 70)
        self.stdout.write(f'{"Filename":<40} {"Size":<10} {"Date":<20}')
        self.stdout.write('-' * 70)

        for f in backups:
            size = f.stat().st_size
            size_str = self._format_size(size)
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            self.stdout.write(f'{f.name:<40} {size_str:<10} {mtime:<20}')

        self.stdout.write(f'\nTotal: {len(backups)} backup(s)')
        self.stdout.write(f'Schedule: {settings.get_schedule_display()}')
        if settings.last_backup_at:
            self.stdout.write(f'Last backup: {settings.last_backup_at.strftime("%Y-%m-%d %H:%M")}')

    def _format_size(self, size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f'{size_bytes:.1f} {unit}'
            size_bytes /= 1024
        return f'{size_bytes:.1f} TB'