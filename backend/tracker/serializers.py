from django.conf import settings
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
            "created_at",
        ]

    def get_minutes(self, obj: Session) -> int:
        return obj.duration_seconds // 60


class ManualSessionInputSerializer(serializers.Serializer):
    metric = serializers.CharField(default=settings.DEFAULT_SESSION_METRIC)
    date = serializers.DateField()
    minutes = serializers.IntegerField(min_value=1)
    note = serializers.CharField(allow_blank=True, default="", trim_whitespace=False)


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
    minutes = serializers.IntegerField(min_value=1)


class FinishTimerSerializer(serializers.Serializer):
    metric = serializers.CharField(default=settings.DEFAULT_SESSION_METRIC)
    note = serializers.CharField(allow_blank=True, default="", trim_whitespace=False)


class TimerActionSerializer(serializers.Serializer):
    metric = serializers.CharField(default=settings.DEFAULT_SESSION_METRIC)


class PreferencesSerializer(serializers.Serializer):
    accent_color = serializers.ChoiceField(choices=settings.ACCENT_COLORS)
