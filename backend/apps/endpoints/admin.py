from django.contrib import admin

from .models import Endpoint


@admin.register(Endpoint)
class EndpointAdmin(admin.ModelAdmin):
    list_display = ("method", "path", "app", "is_active", "last_seen_at", "created_at")
    list_filter = ("method", "is_active")
    search_fields = ("path", "app__name")
    readonly_fields = ("id", "created_at", "updated_at")
