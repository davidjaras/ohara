from django.contrib import admin

from .models import ProgramAccess, TrainingProfile


@admin.register(TrainingProfile)
class TrainingProfileAdmin(admin.ModelAdmin):
    """The only interface for enabling the module and picking a variant."""

    list_display = ["user", "enabled", "active_variant", "weight_unit"]
    list_filter = ["enabled"]
    raw_id_fields = ["user"]


@admin.register(ProgramAccess)
class ProgramAccessAdmin(admin.ModelAdmin):
    """The only interface for granting a user access to a program."""

    list_display = ["user", "program", "granted_at"]
    list_filter = ["program"]
    raw_id_fields = ["user"]
