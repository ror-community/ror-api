# Generated by Django 2.2.28 on 2025-03-11 07:13

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=255)),
                ('name', models.CharField(blank=True, max_length=255)),
                ('institution_name', models.CharField(blank=True, max_length=255)),
                ('institution_ror', models.URLField(blank=True, max_length=255)),
                ('country_code', models.CharField(blank=True, max_length=2)),
                ('ror_use', models.TextField(blank=True, max_length=500)),
                ('client_id', models.CharField(editable=False, max_length=32, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_request_at', models.DateTimeField(blank=True, null=True)),
                ('request_count', models.IntegerField(default=0)),
            ],
        ),
    ]
