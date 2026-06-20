from datetime import timedelta

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone


class Command(BaseCommand):
    help = 'Check backup schedule and run backup if due (called by cron)'

    def handle(self, *args, **options):
        from inventory.models import BackupSettings

        settings = BackupSettings.get_settings()

        if settings.schedule == BackupSettings.Schedule.DISABLED:
            self.stdout.write('Scheduled backups are disabled.')
            return

        # Determine interval
        intervals = {
            BackupSettings.Schedule.DAILY: timedelta(days=1),
            BackupSettings.Schedule.WEEKLY: timedelta(weeks=1),
            BackupSettings.Schedule.MONTHLY: timedelta(days=30),
        }

        interval = intervals.get(settings.schedule)
        if not interval:
            self.stdout.write('Unknown schedule setting.')
            return

        # Check if backup is due
        now = timezone.now()
        if settings.last_backup_at:
            next_backup_due = settings.last_backup_at + interval
            if now < next_backup_due:
                self.stdout.write(
                    f'Next backup not due until {next_backup_due.strftime("%Y-%m-%d %H:%M")}. Skipping.'
                )
                return

        # Run backup
        self.stdout.write(f'Running scheduled {settings.get_schedule_display()} backup...')
        try:
            call_command('backup_db', '--compress')
            self.stdout.write(self.style.SUCCESS('Scheduled backup completed.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Scheduled backup failed: {e}'))