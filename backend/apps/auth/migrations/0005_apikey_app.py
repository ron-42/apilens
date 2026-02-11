"""Step 1: Add nullable app FK to ApiKey."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("apps_auth", "0004_apikey"),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="apikey",
            name="app",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="api_keys",
                to="projects.app",
            ),
        ),
    ]
