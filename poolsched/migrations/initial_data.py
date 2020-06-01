from django.db import migrations
from ..models.targets.github import Instance

def github_data(apps, schema_editor):
    """Add data for GitHub"""
    Instance.objects.update_or_create(
        name='GitHub',
        endpoint="https://api.github.com")

class Migration(migrations.Migration):

    dependencies = [
        ('poolsched', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(github_data)
    ]
