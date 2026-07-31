from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import Measurement, Session


class SessionSerializer(serializers.ModelSerializer):
    minutes = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            "id",
            "metric",
            "date",
            "duration_seconds",
            "minutes",
            "note",
            "started_at",
            "ended_at",
            "close_reason",
            "estimated_duration_seconds",
            "needs_review",
            "created_at",
        ]

    def get_minutes(self, obj: Session) -> int:
        return obj.duration_seconds // 60


class ManualSessionInputSerializer(serializers.Serializer):
    metric = serializers.CharField(default=settings.DEFAULT_SESSION_METRIC)
    date = serializers.DateField()
    minutes = serializers.IntegerField(min_value=1, max_value=settings.MAX_DAY_MINUTES)
    note = serializers.CharField(allow_blank=True, default="", trim_whitespace=False)


class SessionUpdateInputSerializer(serializers.Serializer):
    """Partial edit of an existing session: only the given fields change."""

    date = serializers.DateField(required=False)
    minutes = serializers.IntegerField(
        min_value=1, max_value=settings.MAX_DAY_MINUTES, required=False
    )
    note = serializers.CharField(
        allow_blank=True, required=False, trim_whitespace=False
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(_("Nothing to update."))
        return attrs


class MeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Measurement
        fields = ["id", "metric", "date", "value", "note", "created_at"]


class MeasurementInputSerializer(serializers.Serializer):
    metric = serializers.CharField()
    date = serializers.DateField()
    value = serializers.DecimalField(max_digits=8, decimal_places=2)
    note = serializers.CharField(allow_blank=True, default="", trim_whitespace=False)


class GoalInputSerializer(serializers.Serializer):
    metric = serializers.CharField(default=settings.DEFAULT_SESSION_METRIC)
    minutes = serializers.IntegerField(min_value=1, max_value=settings.MAX_WEEK_MINUTES)


class FinishTimerSerializer(serializers.Serializer):
    metric = serializers.CharField(default=settings.DEFAULT_SESSION_METRIC)
    note = serializers.CharField(allow_blank=True, default="", trim_whitespace=False)


class TimerActionSerializer(serializers.Serializer):
    metric = serializers.CharField(default=settings.DEFAULT_SESSION_METRIC)


class StartTimerSerializer(serializers.Serializer):
    metric = serializers.CharField(default=settings.DEFAULT_SESSION_METRIC)
    planned_minutes = serializers.IntegerField(
        min_value=1,
        max_value=settings.MAX_DAY_MINUTES,
        required=False,
        allow_null=True,
        default=None,
    )


class ExtendTimerSerializer(serializers.Serializer):
    metric = serializers.CharField(default=settings.DEFAULT_SESSION_METRIC)
    minutes = serializers.IntegerField(min_value=1, max_value=settings.MAX_DAY_MINUTES)


class SessionReviewInputSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["confirm", "adjust"])
    ended_at = serializers.DateTimeField(required=False, allow_null=True, default=None)
    note = serializers.CharField(
        allow_blank=True, required=False, default="", trim_whitespace=False
    )


class PreferencesSerializer(serializers.Serializer):
    accent_color = serializers.ChoiceField(choices=settings.ACCENT_COLORS)
