from django.contrib import admin

from .models import ActiveTimer, Measurement, Session, UserPreference, WeeklyGoal


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ["user", "metric", "date", "duration_seconds", "created_at"]
    list_filter = ["metric", "user"]
    date_hierarchy = "date"


@admin.register(ActiveTimer)
class ActiveTimerAdmin(admin.ModelAdmin):
    list_display = ["user", "metric", "started_at", "running_since"]


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ["user", "metric", "date", "value"]
    list_filter = ["metric", "user"]


@admin.register(WeeklyGoal)
class WeeklyGoalAdmin(admin.ModelAdmin):
    list_display = ["user", "metric", "week_start", "minutes"]
    list_filter = ["metric", "user"]


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "accent_color"]
