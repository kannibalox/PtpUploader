# Generated by Django 3.2.9 on 2022-01-08 21:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0013_auto_20211104_0344'),
    ]

    operations = [
        migrations.RenameField(
            model_name='releaseinfo',
            old_name='ScheduleTimeUtc',
            new_name='ScheduleTime',
        ),
    ]
