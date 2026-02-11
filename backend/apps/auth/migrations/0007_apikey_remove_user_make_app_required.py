"""Step 3: Make app NOT NULL, remove user FK from ApiKey."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("apps_auth", "0006_migrate_apikeys_to_apps"),
    ]

    operations = [
        # Make app non-nullable
        migrations.AlterField(
            model_name="apikey",
            name="app",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="api_keys",
                to="projects.app",
            ),
        ),
        # Remove old user FK
        migrations.RemoveField(
            model_name="apikey",
            name="user",
        ),
    ]
