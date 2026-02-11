from django.contrib import admin

from .models import App


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "slug", "owner", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "slug", "owner__email"]
    readonly_fields = ["id", "slug", "created_at", "updated_at"]
    raw_id_fields = ["owner"]
