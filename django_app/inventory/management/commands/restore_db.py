import os
import subprocess
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Restore a PostgreSQL database from a backup file'

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_file',
            type=str,
            help='Path to the backup file (.sql or .sql.gz)'
        )
        parser.add_argument(
            '--no-confirm',
            action='store_true',
            help='Skip confirmation prompt (for scripting)'
        )

    def handle(self, *args, **options):
        backup_file = Path(options['backup_file'])

        if not backup_file.exists():
            raise CommandError(f'Backup file not found: {backup_file}')

        if not backup_file.is_file():
            raise CommandError(f'Not a file: {backup_file}')

        # Confirmation
        if not options['no_confirm']:
            self.stdout.write(self.style.WARNING(
                f'\n⚠️  WARNING: This will OVERWRITE the current database!\n'
                f'   Backup file: {backup_file}\n'
                f'   Database: {settings.DATABASES["default"]["NAME"]}\n'
            ))
            confirm = input('Type "yes" to confirm: ')
            if confirm.lower() != 'yes':
                self.stdout.write('Restore cancelled.')
                return

        # Database settings
        db_settings = settings.DATABASES['default']
        db_name = db_settings['NAME']
        db_user = db_settings['USER']
        db_password = db_settings['PASSWORD']
        db_host = db_settings.get('HOST', 'db')
        db_port = db_settings.get('PORT', '5432')

        env = os.environ.copy()
        env['PGPASSWORD'] = db_password

        psql_cmd = [
            'psql',
            '-h', db_host,
            '-p', str(db_port),
            '-U', db_user,
            '-d', db_name,
        ]

        self.stdout.write('Dropping existing tables...')

        # Drop all tables in public schema before restore
        drop_sql = """
        DO $$ DECLARE
            r RECORD;
        BEGIN
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
            END LOOP;
        END $$;
        """

        try:
            subprocess.run(
                psql_cmd + ['-c', drop_sql],
                env=env, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as e:
            raise CommandError(f'Failed to drop tables: {e.stderr.decode()}')

        self.stdout.write(f'Restoring from: {backup_file}')

        try:
            is_gzipped = str(backup_file).endswith('.gz')

            if is_gzipped:
                gunzip_proc = subprocess.Popen(
                    ['gunzip', '-c', str(backup_file)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                result = subprocess.run(
                    psql_cmd,
                    stdin=gunzip_proc.stdout,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                gunzip_proc.stdout.close()
                gunzip_proc.wait()

                if gunzip_proc.returncode != 0:
                    raise CommandError(f'gunzip failed: {gunzip_proc.stderr.read().decode()}')
            else:
                with open(backup_file, 'r') as f:
                    result = subprocess.run(
                        psql_cmd,
                        stdin=f,
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )

            if result.returncode != 0:
                self.stdout.write(self.style.WARNING(
                    f'psql returned code {result.returncode}. '
                    f'Some non-critical errors may have occurred.'
                ))
                if result.stderr:
                    self.stdout.write(result.stderr.decode()[:1000])
            else:
                self.stdout.write(self.style.SUCCESS('Database restored successfully!'))

            self.stdout.write('\nRunning migrations to ensure schema is up to date...')
            from django.core.management import call_command
            call_command('migrate', '--noinput')

            self.stdout.write(self.style.SUCCESS('Restore complete.'))

        except subprocess.CalledProcessError as e:
            raise CommandError(f'Restore failed: {e.stderr.decode() if e.stderr else str(e)}')