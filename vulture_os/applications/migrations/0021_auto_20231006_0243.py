# Generated by Django 3.2.21 on 2023-10-06 02:43

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import djongo.models.fields

kafka_params = {}

def save_kafka_params(apps, schema_editor):
    kafka_forwarders_model = apps.get_model("applications", "LogOMKAFKA")
    db_alias = schema_editor.connection.alias
    kafka_forwarders = kafka_forwarders_model.objects.using(db_alias)

    for fwd in kafka_forwarders.all():
        kafka_params[fwd.name] = {
            "confParam": fwd.confParam,
            "topicConfParam": fwd.topicConfParam
        }


def restore_kafka_params(apps, schema_editor):
    kafka_forwarders_model = apps.get_model("applications", "LogOMKAFKA")
    db_alias = schema_editor.connection.alias
    kafka_forwarders = kafka_forwarders_model.objects.using(db_alias)

    for fwd in kafka_forwarders.all():
        # Forward conversion
        if isinstance(kafka_params[fwd.name]['confParam'], str):
            fwd.confParam = list()
            fwd.topicConfParam = list()
            for kv in kafka_params[fwd.name]['confParam'].split(','):
                fwd.confParam.append(kv.strip())
            for kv in kafka_params[fwd.name]['topicConfParam'].split(','):
                fwd.topicConfParam.append(kv.strip())
        # Reverse convertion
        elif isinstance(kafka_params[fwd.name]['confParam'], list):
            fwd.confParam = ", ".join(kafka_params[fwd.name]['confParam'])
            fwd.topicConfParam = ", ".join(kafka_params[fwd.name]['topicConfParam'])

        else:
            fwd.confParam = list()
            fwd.topicConfParam = list()
        fwd.save()
        print(f"'{fwd.name}' params updated")


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0022_alter_tlsprofile_protocols'),
        ('applications', '0020_auto_20230822_0926'),
    ]

    operations = [
        migrations.AddField(
            model_name='logom',
            name='max_workers',
            field=models.PositiveIntegerField(blank=True, help_text='Maximum workers created for the output', null=True, validators=[django.core.validators.MinValueValidator(1)], verbose_name='Queue max workers'),
        ),
        migrations.AddField(
            model_name='logom',
            name='new_worker_minimum_messages',
            field=models.PositiveIntegerField(blank=True, help_text='Number of messages in queue to start a new worker thread', null=True, validators=[django.core.validators.MinValueValidator(1)], verbose_name='Minimum messages to start a new worker'),
        ),
        migrations.AddField(
            model_name='logom',
            name='queue_timeout_shutdown',
            field=models.PositiveIntegerField(blank=True, help_text='Time to wait for the queue to finish processing entries (in ms)', null=True, validators=[django.core.validators.MinValueValidator(1)], verbose_name='Queue timeout shutdown (ms)'),
        ),
        migrations.AddField(
            model_name='logom',
            name='worker_timeout_shutdown',
            field=models.PositiveIntegerField(blank=True, help_text='Inactivity delay after which to stop a worker (in ms)', null=True, validators=[django.core.validators.MinValueValidator(1)], verbose_name='Worker inactivity shutdown delay (ms)'),
        ),
        migrations.AlterField(
            model_name='backend',
            name='tcp_health_check_expect_match',
            field=models.TextField(choices=[('', 'None'), ('string', 'Response content contains'), ('rstring', 'Response content match regex'), ('binary', 'Response binary contains'), ('rbinary', 'Response binary match regex'), ('! string', 'Response content does not contain'), ('! rstring', 'Response content does not match regex'), ('! binary', 'Response binary does not contains'), ('! rbinary', 'Response binary does not match regex')], default='', help_text='Type of match to expect', verbose_name='TCP Health Check expected'),
        ),
        migrations.RunPython(save_kafka_params, restore_kafka_params),
        migrations.RemoveField(
            model_name="logomkafka",
            name="confParam",
        ),
        migrations.RemoveField(
            model_name="logomkafka",
            name="topicConfParam",
        ),
        migrations.AddField(
            model_name="logomkafka",
            name="confParam",
            field=djongo.models.fields.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="logomkafka",
            name="topicConfParam",
            field=djongo.models.fields.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(restore_kafka_params, save_kafka_params),
    ]
