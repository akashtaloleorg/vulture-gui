# Generated by Django 3.2.20 on 2023-07-19 21:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0056_auto_20230622_1701'),
    ]

    operations = [
        migrations.AddField(
            model_name='frontend',
            name='csc_domainmanager_apikey',
            field=models.TextField(default='', help_text='CSC DomainManager API Key', verbose_name='CSC DomainManager API Key'),
        ),
        migrations.AddField(
            model_name='frontend',
            name='csc_domainmanager_authorization',
            field=models.TextField(default='', help_text='CSC DomainManager Authorization', verbose_name='CSC DomainManager Authorization HTTP Header token prefixed by Bearer, ex: Bearer xxxx-xxxx-xxxx-xxxx'),
        ),
        migrations.AddField(
            model_name='frontend',
            name='sentinel_one_account_type',
            field=models.TextField(choices=[('console', 'console'), ('user service', 'user service')], default='console', help_text='Type of account : console or user service', verbose_name='Sentinel One Account type'),
        ),
        migrations.AddField(
            model_name='frontend',
            name='sentinel_one_mobile_apikey',
            field=models.TextField(default='', help_text='Sentinel One Mobile API integration key', verbose_name='Sentinel One Mobile API ikey'),
        ),
        migrations.AddField(
            model_name='frontend',
            name='sentinel_one_mobile_host',
            field=models.TextField(default='https://xxx.mobile.sentinelone.net', help_text='Sentinel One Mobile API hostname', verbose_name='Sentinel One Mobile API hostname'),
        ),
    ]
