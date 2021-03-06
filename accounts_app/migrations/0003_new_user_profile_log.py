# Generated by Django 2.1 on 2018-08-26 19:52

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('accounts_app', '0002_auto_20180807_1548'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfileLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meta_info', jsonfield.fields.JSONField(default=dict, verbose_name='Meta information')),
                ('do_type', models.CharField(choices=[('cusr', 'Create user'), ('dusr', 'Delete user'), ('cdev', 'Create device'), ('ddev', 'Delete device'), ('cnas', 'Create NAS'), ('dnas', 'Delete NAS'), ('csrv', 'Create service'), ('dsrv', 'Delete service')], max_length=4, verbose_name='Action type')),
                ('additional_text', models.CharField(blank=True, null=True, verbose_name='Additional info', max_length=512)),
                ('action_date', models.DateTimeField(auto_now_add=True, verbose_name='Action date')),
            ],
            options={
                'verbose_name': 'User profile log',
                'verbose_name_plural': 'User profile logs',
                'ordering': ('-action_date',),
            },
        ),
        migrations.AlterModelOptions(
            name='userprofile',
            options={'ordering': ('fio',), 'verbose_name': 'Staff account profile', 'verbose_name_plural': 'Staff account profiles'},
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='avatar',
            field=models.ImageField(blank=True, default=None, null=True, upload_to='user/avatar', verbose_name='Avatar'),
        ),
        migrations.AddField(
            model_name='userprofilelog',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Author'),
        ),
    ]
