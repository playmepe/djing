# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-01-23 13:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('abonapp', '0004_auto_20180122_1732'),
    ]

    operations = [
        migrations.AlterField(
            model_name='alltimepaylog',
            name='receipt_num',
            field=models.BigIntegerField(default=0, verbose_name='Receipt number'),
        ),
    ]