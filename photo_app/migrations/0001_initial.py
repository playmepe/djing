# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-06-28 23:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Photo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(height_field=b'heigt', upload_to=b'', width_field=b'wdth')),
                ('wdth', models.PositiveSmallIntegerField(blank=True, default=b'759', editable=False, null=True)),
                ('heigt', models.PositiveSmallIntegerField(blank=True, editable=False, null=True)),
            ],
        ),
    ]
