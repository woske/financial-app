# Generated by Django 4.1.1 on 2023-01-31 23:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0004_alter_account_user'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='account',
            name='user',
        ),
    ]
