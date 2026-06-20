from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_userprofile'),
    ]

    operations = [
        migrations.CreateModel(
            name='BackupSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('schedule', models.CharField(
                    choices=[('disabled', 'Disabled'), ('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')],
                    default='disabled', help_text='How often automatic backups should run', max_length=20
                )),
                ('retention_days', models.PositiveIntegerField(
                    default=30, help_text='Delete backups older than this many days (0 = keep forever)'
                )),
                ('backup_dir', models.CharField(
                    default='/app/backups', help_text='Directory where backup files are stored', max_length=500
                )),
                ('last_backup_at', models.DateTimeField(blank=True, null=True)),
                ('last_backup_file', models.CharField(blank=True, default='', max_length=500)),
                ('last_backup_status', models.CharField(blank=True, default='', max_length=50)),
            ],
            options={
                'verbose_name': 'Backup Settings',
                'verbose_name_plural': 'Backup Settings',
            },
        ),
    ]