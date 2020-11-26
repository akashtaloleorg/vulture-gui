# Generated by Django 2.1.3 on 2020-11-19 16:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0004_auto_20201119_1559'),
    ]

    operations = [
        migrations.AlterField(
            model_name='openidrepository',
            name='authorization_endpoint',
            field=models.TextField(default='', help_text='', verbose_name='Authorization url'),
        ),
        migrations.AlterField(
            model_name='openidrepository',
            name='end_session_endpoint',
            field=models.TextField(default='', help_text='', verbose_name='Disconnect url'),
        ),
        migrations.AlterField(
            model_name='openidrepository',
            name='issuer',
            field=models.TextField(default='', help_text='', verbose_name='Issuer to use'),
        ),
        migrations.AlterField(
            model_name='openidrepository',
            name='token_endpoint',
            field=models.TextField(default='', help_text='', verbose_name='Get token url'),
        ),
        migrations.AlterField(
            model_name='openidrepository',
            name='userinfo_endpoint',
            field=models.TextField(default='', help_text='', verbose_name='Get user infos url'),
        ),
        migrations.AlterField(
            model_name='userauthentication',
            name='sso_forward_capture_content',
            field=models.TextField(default='^REGEX to capture (content.*) in SSO Forward Response$', help_text=''),
        ),
        migrations.AlterField(
            model_name='userauthentication',
            name='sso_forward_content',
            field=models.TextField(default='', help_text=''),
        ),
    ]
