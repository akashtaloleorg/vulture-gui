# Generated by Django 3.0.5 on 2021-11-24 09:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0034_auto_20210928_1520'),
    ]

    operations = [
        migrations.AddField(
            model_name='frontend',
            name='defender_client_id',
            field=models.TextField(default='', help_text="Client id of the OAuth endpoint to get an OAuth token before requesting Microsoft's APIs", verbose_name='Defender OAuth client id'),
        ),
        migrations.AddField(
            model_name='frontend',
            name='defender_client_secret',
            field=models.TextField(default='', help_text="Client secret of the OAuth endpoint to get an OAuth token before requesting Microsoft's APIs", verbose_name='Defender OAuth client secret'),
        ),
        migrations.AddField(
            model_name='frontend',
            name='defender_token_endpoint',
            field=models.TextField(default='', help_text="Complete enpoint address to get an Oauth token before requesting Microsoft's APIs", verbose_name='Defender token endpoint'),
        ),
        migrations.AddField(
            model_name='frontend',
            name='vadesecure_host',
            field=models.TextField(default='', help_text='Hostname (without scheme or path) of the Vadesecure server', verbose_name='Vadesecure Host'),
        ),
        migrations.AddField(
            model_name='frontend',
            name='vadesecure_login',
            field=models.TextField(default='', help_text='Login used to fetch the token for the Vadesecure API', verbose_name='Vadesecure login'),
        ),
        migrations.AddField(
            model_name='frontend',
            name='vadesecure_password',
            field=models.TextField(default='', help_text='Password used to fetch the token for the Vadesecure API', verbose_name='Vadesecure password'),
        ),
        migrations.AlterField(
            model_name='frontend',
            name='filebeat_module',
            field=models.TextField(choices=[('_custom', 'Custom Filebeat config'), ('activemq', 'Activemq'), ('aws', 'Aws'), ('awsfargate', 'Awsfargate'), ('azure', 'Azure'), ('barracuda', 'Barracuda'), ('bluecoat', 'Bluecoat'), ('cef', 'Cef'), ('checkpoint', 'Checkpoint'), ('cisco', 'Cisco'), ('coredns', 'Coredns'), ('crowdstrike', 'Crowdstrike'), ('cyberark', 'Cyberark'), ('cyberarkpas', 'Cyberarkpas'), ('cylance', 'Cylance'), ('envoyproxy', 'Envoyproxy'), ('f5', 'F5'), ('fortinet', 'Fortinet'), ('gcp', 'Gcp'), ('google_workspace', 'Google_workspace'), ('googlecloud', 'Googlecloud'), ('gsuite', 'Gsuite'), ('ibmmq', 'Ibmmq'), ('imperva', 'Imperva'), ('infoblox', 'Infoblox'), ('iptables', 'Iptables'), ('juniper', 'Juniper'), ('microsoft', 'Microsoft'), ('misp', 'Misp'), ('mssql', 'Mssql'), ('mysqlenterprise', 'Mysqlenterprise'), ('netflow', 'Netflow'), ('netscout', 'Netscout'), ('o365', 'O365'), ('okta', 'Okta'), ('oracle', 'Oracle'), ('panw', 'Panw'), ('proofpoint', 'Proofpoint'), ('rabbitmq', 'Rabbitmq'), ('radware', 'Radware'), ('snort', 'Snort'), ('snyk', 'Snyk'), ('sonicwall', 'Sonicwall'), ('sophos', 'Sophos'), ('squid', 'Squid'), ('suricata', 'Suricata'), ('threatintel', 'Threatintel'), ('tomcat', 'Tomcat'), ('zeek', 'Zeek'), ('zookeeper', 'Zookeeper'), ('zoom', 'Zoom'), ('zscaler', 'Zscaler')], default='tcp', help_text='Filebeat built-in module'),
        ),
    ]
