# Manual migration: ApiKey user FK → app FK
# The DB already has app_id and no user_id column, so this is faked.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("apps_auth", "0002_initial"),
        ("projects", "0002_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="apikey",
            name="user",
        ),
        migrations.AddField(
            model_name="apikey",
            name="app",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="api_keys",
                to="projects.app",
            ),
            preserve_default=False,
        ),
    ]
