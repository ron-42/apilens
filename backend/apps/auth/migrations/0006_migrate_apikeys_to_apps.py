"""Step 2: Data migration — create Default App per user, assign API keys."""

from django.db import migrations


def forward(apps, schema_editor):
    ApiKey = apps.get_model("apps_auth", "ApiKey")
    App = apps.get_model("projects", "App")
    User = apps.get_model("users", "User")

    # Find all users who have at least one API key (force evaluate with list)
    user_ids = list(
        ApiKey.objects.filter(app__isnull=True)
        .values_list("user_id", flat=True)
        .distinct()
    )

    for user_id in user_ids:
        user = User.objects.get(id=user_id)
        default_app, _ = App.objects.get_or_create(
            owner=user,
            slug="default-app",
            defaults={
                "name": "Default App",
                "description": "Auto-created app for existing API keys",
            },
        )
        ApiKey.objects.filter(user=user, app__isnull=True).update(app=default_app)


def backward(apps, schema_editor):
    ApiKey = apps.get_model("apps_auth", "ApiKey")
    App = apps.get_model("projects", "App")

    # Move API keys back to user from app.owner
    for api_key in ApiKey.objects.filter(app__isnull=False).select_related("app"):
        ApiKey.objects.filter(id=api_key.id).update(user=api_key.app.owner_id)

    # Delete auto-created default apps
    App.objects.filter(name="Default App", slug="default-app").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("apps_auth", "0005_apikey_app"),
        ("projects", "0001_initial"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
