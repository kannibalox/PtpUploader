# Generated by Django 3.2.8 on 2021-11-04 03:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0012_alter_releaseinfo_screenshots'),
    ]

    operations = [
        migrations.AlterField(
            model_name='releaseinfo',
            name='Size',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='releaseinfo',
            name='Type',
            field=models.TextField(blank=True, choices=[('Feature Film', 'Feature Film'), ('Short Film', 'Short Film'), ('Miniseries', 'Miniseries'), ('Stand-up Comedy', 'Stand-up Comedy'), ('Concert', 'Concert'), ('Live Performance', 'Live Performance'), ('Movie Collection', 'Movie Collection')], default='Feature Film'),
        ),
    ]
