# Generated by Django 3.2.5 on 2021-10-29 20:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0007_alter_releaseinfo_trumpable'),
    ]

    operations = [
        migrations.AlterField(
            model_name='releaseinfo',
            name='Subtitles',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
