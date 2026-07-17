from dataclasses import asdict

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .metrics import get_metric, list_metrics
from .models import ActiveTimer, Measurement, Session
from .serializers import (
    FinishTimerSerializer,
    GoalInputSerializer,
    ManualSessionInputSerializer,
    MeasurementInputSerializer,
    MeasurementSerializer,
    SessionSerializer,
    TimerActionSerializer,
)


def _error(message: str, code: int) -> Response:
    return Response({"detail": message}, status=code)


def _timer_state(timer: ActiveTimer | None) -> dict:
    if timer is None:
        return {"active": False}
    now = timezone.now()
    return {
        "active": True,
        "metric": timer.metric,
        "started_at": timer.started_at,
        "is_paused": timer.is_paused,
        "elapsed_seconds": timer.elapsed_seconds(now),
        "server_time": now,
    }


class MeView(APIView):
    def get(self, request):
        return Response({"username": request.user.username})


class MetricListView(APIView):
    def get(self, request):
        return Response([asdict(m) for m in list_metrics()])


class TimerView(APIView):
    """State and discard of the active timer."""

    def get(self, request):
        metric = request.query_params.get("metric", settings.DEFAULT_SESSION_METRIC)
        timer = ActiveTimer.objects.filter(user=request.user, metric=metric).first()
        return Response(_timer_state(timer))

    def delete(self, request):
        metric = request.query_params.get("metric", settings.DEFAULT_SESSION_METRIC)
        try:
            services.discard_timer(request.user, metric)
        except services.TimerError as e:
            return _error(str(e), status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TimerActionView(APIView):
    """POST /api/timer/<action>/ with action in start|pause|resume."""

    actions = {
        "start": services.start_timer,
        "pause": services.pause_timer,
        "resume": services.resume_timer,
    }

    def post(self, request, action: str):
        if action not in self.actions:
            return _error(_("Invalid action."), status.HTTP_404_NOT_FOUND)
        serializer = TimerActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        metric = serializer.validated_data["metric"]
        try:
            timer = self.actions[action](request.user, metric, timezone.now())
        except services.TimerError as e:
            return _error(str(e), status.HTTP_409_CONFLICT)
        except ValueError as e:
            return _error(str(e), status.HTTP_400_BAD_REQUEST)
        return Response(_timer_state(timer))


class TimerFinishView(APIView):
    def post(self, request):
        serializer = FinishTimerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            session = services.finish_timer(
                request.user, data["metric"], timezone.now(), data["note"]
            )
        except services.TimerError as e:
            return _error(str(e), status.HTTP_409_CONFLICT)
        return Response(SessionSerializer(session).data, status=status.HTTP_201_CREATED)


class SessionListView(APIView):
    def get(self, request):
        metric = request.query_params.get("metric", settings.DEFAULT_SESSION_METRIC)
        limit = int(request.query_params.get("limit", settings.DEFAULT_SESSION_LIMIT))
        sessions = Session.objects.filter(user=request.user, metric=metric)[:limit]
        return Response(SessionSerializer(sessions, many=True).data)

    def post(self, request):
        serializer = ManualSessionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            session = services.log_manual_session(
                request.user, data["metric"], data["date"], data["minutes"], data["note"]
            )
        except ValueError as e:
            return _error(str(e), status.HTTP_400_BAD_REQUEST)
        return Response(SessionSerializer(session).data, status=status.HTTP_201_CREATED)


class SessionDetailView(APIView):
    def delete(self, request, pk: int):
        deleted, _count = Session.objects.filter(user=request.user, pk=pk).delete()
        if not deleted:
            return _error(_("No such session."), status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeasurementListView(APIView):
    def get(self, request):
        metric = request.query_params.get("metric")
        if not metric:
            return _error(_("Missing metric parameter."), status.HTTP_400_BAD_REQUEST)
        limit = int(request.query_params.get("limit", settings.DEFAULT_MEASUREMENT_LIMIT))
        rows = Measurement.objects.filter(user=request.user, metric=metric)[:limit]
        return Response(MeasurementSerializer(rows, many=True).data)

    def post(self, request):
        serializer = MeasurementInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            row = services.log_measurement(
                request.user, data["metric"], data["date"], data["value"], data["note"]
            )
        except ValueError as e:
            return _error(str(e), status.HTTP_400_BAD_REQUEST)
        return Response(MeasurementSerializer(row).data, status=status.HTTP_201_CREATED)


class MeasurementDetailView(APIView):
    def delete(self, request, pk: int):
        deleted, _count = Measurement.objects.filter(user=request.user, pk=pk).delete()
        if not deleted:
            return _error(_("No such measurement."), status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class GoalView(APIView):
    def get(self, request):
        metric_key = request.query_params.get("metric", settings.DEFAULT_SESSION_METRIC)
        try:
            metric = get_metric(metric_key)
        except ValueError as e:
            return _error(str(e), status.HTTP_400_BAD_REQUEST)
        week = services.week_start(timezone.localdate())
        return Response(
            {
                "metric": metric_key,
                "minutes": services.goal_for_week(request.user, metric, week),
            }
        )

    def put(self, request):
        serializer = GoalInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            row = services.set_goal(
                request.user, data["metric"], data["minutes"], timezone.localdate()
            )
        except ValueError as e:
            return _error(str(e), status.HTTP_400_BAD_REQUEST)
        return Response({"metric": row.metric, "minutes": row.minutes})


class StatsView(APIView):
    """Full dashboard payload in a single call."""

    def get(self, request):
        metric_key = request.query_params.get("metric", settings.DEFAULT_SESSION_METRIC)
        weeks = int(request.query_params.get("weeks", settings.DEFAULT_STATS_WEEKS))
        today = timezone.localdate()
        try:
            weekly = services.weekly_summaries(request.user, metric_key, today, weeks)
            streak = services.current_streak(request.user, metric_key, today)
            cumulative = services.week_cumulative(request.user, metric_key, today)
        except ValueError as e:
            return _error(str(e), status.HTTP_400_BAD_REQUEST)
        this_week = weekly[-1]
        return Response(
            {
                "metric": metric_key,
                "today": today,
                "week_minutes": this_week.minutes,
                "week_goal_minutes": this_week.goal_minutes,
                "week_met": this_week.met,
                "streak_weeks": streak,
                "total_minutes": services.total_minutes(request.user, metric_key),
                "week_cumulative": cumulative,
                "weekly": [asdict(w) for w in weekly],
            }
        )
