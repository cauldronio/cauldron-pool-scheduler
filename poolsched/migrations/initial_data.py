from django.db import migrations
from ..models.targets.github import GHInstance
from ..models.targets.gitlab import GLInstance


def github_data(apps, schema_editor):
    """Add data for GitHub"""
    GHInstance.objects.update_or_create(
        name='GitHub',
        endpoint="https://github.com")


def gitlab_data(apps, schema_editor):
    GLInstance.objects.update_or_create(
        name='GitLab',
        endpoint="https://gitlab.com")


class Migration(migrations.Migration):

    dependencies = [
        ('poolsched', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(github_data),
        migrations.RunPython(gitlab_data)
    ]
