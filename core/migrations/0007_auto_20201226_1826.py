# Generated by Django 3.0.4 on 2020-12-26 18:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_keycloakrealm'),
    ]

    operations = [
        migrations.AddField(
            model_name='keycloakrealm',
            name='admin',
            field=models.EmailField(blank=True, default='admin@abigbot.com', max_length=254, null=True),
        ),
        migrations.AddField(
            model_name='keycloakrealm',
            name='password',
            field=models.TextField(blank=True, default='', null=True),
        ),
    ]
