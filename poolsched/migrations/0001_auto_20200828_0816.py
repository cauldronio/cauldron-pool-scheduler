# Generated by Django 3.0.6 on 2020-08-28 08:16

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('poolsched', 'initial_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='intention',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name='IGLRawArchived',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField()),
                ('completed', models.DateTimeField(auto_now_add=True)),
                ('repo', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='poolsched.GLRepo')),
                ('user', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='IGLEnrichArchived',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField()),
                ('completed', models.DateTimeField(auto_now_add=True)),
                ('repo', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='poolsched.GLRepo')),
                ('user', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='IGitRawArchived',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField()),
                ('completed', models.DateTimeField(auto_now_add=True)),
                ('repo', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='poolsched.GitRepo')),
                ('user', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='IGitEnrichArchived',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField()),
                ('completed', models.DateTimeField(auto_now_add=True)),
                ('repo', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='poolsched.GitRepo')),
                ('user', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='IGHRawArchived',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField()),
                ('completed', models.DateTimeField(auto_now_add=True)),
                ('repo', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='poolsched.GHRepo')),
                ('user', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='IGHEnrichArchived',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField()),
                ('completed', models.DateTimeField(auto_now_add=True)),
                ('repo', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='poolsched.GHRepo')),
                ('user', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]