# Generated by Django 2.1.3 on 2019-02-13 05:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0007_auto_20190212_0815'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='config',
            name='description',
        ),
    ]