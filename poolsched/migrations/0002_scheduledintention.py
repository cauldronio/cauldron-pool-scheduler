# Generated by Django 3.1.1 on 2021-11-04 16:39

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('poolsched', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScheduledIntention',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('intention_class', models.CharField(max_length=250)),
                ('kwargs', models.JSONField()),
                ('scheduled_at', models.DateTimeField(default=None, null=True)),
                ('repeat', models.IntegerField(default=24, null=True)),
                ('depends_on', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children_intentions', to='poolsched.scheduledintention')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('worker', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='poolsched.worker')),
            ],
        ),
    ]
