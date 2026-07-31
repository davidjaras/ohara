from dataclasses import asdict

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .metrics import get_metric, list_metrics
from .models import ActiveTimer, Measurement, Session, UserPreference
from .serializers import (
    ExtendTimerSerializer,
    FinishTimerSerializer,
    GoalInputSerializer,
    ManualSessionInputSerializer,
    MeasurementInputSerializer,
    MeasurementSerializer,
    PreferencesSerializer,
    SessionReviewInputSerializer,
    SessionSerializer,
    SessionUpdateInputSerializer,
    StartTimerSerializer,
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
        "planned_duration_seconds": timer.planned_duration_seconds,
        "grace_seconds": settings.TIMER_GRACE_SECONDS,
        "reminder_interval_seconds": timer.reminder_interval_seconds,
        "confirmed_seconds": timer.confirmed_seconds,
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
        services.finalize_expired_timer(request.user, metric, timezone.now())
        timer = ActiveTimer.objects.filter(user=request.user, metric=metric).first()
        return Response(_timer_state(timer))

    def delete(self, request):
        metric = request.query_params.get("metric", settings.DEFAULT_SESSION_METRIC)
        try:
            services.discard_timer(request.user, metric)
        except services.TimerError as e:
            return _error(str(e), status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TimerStartView(APIView):
    def post(self, request):
        serializer = StartTimerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        now = timezone.now()
        # An expired timer must not block the new session: it closes into a
        # pending-review row and the fresh one starts on top.
        services.finalize_expired_timer(request.user, data["metric"], now)
        try:
            timer = services.start_timer(
                request.user, data["metric"], now, data["planned_minutes"]
            )
        except services.TimerError as e:
            return _error(str(e), status.HTTP_409_CONFLICT)
        except ValueError as e:
            return _error(str(e), status.HTTP_400_BAD_REQUEST)
        return Response(_timer_state(timer))


class TimerActionView(APIView):
    """POST /api/timer/<action>/ with action in pause|resume."""

    actions = {
        "pause": services.pause_timer,
        "resume": services.resume_timer,
    }

    def post(self, request, action: str):
        if action not in self.actions:
            return _error(_("Invalid action."), status.HTTP_404_NOT_FOUND)
        serializer = TimerActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        metric = serializer.validated_data["metric"]
        now = timezone.now()
        # Acting on an expired timer first closes it, then reports 409: the
        # client refetches and lands on the review banner.
        services.finalize_expired_timer(request.user, metric, now)
        try:
            timer = self.actions[action](request.user, metric, now)
        except services.TimerError as e:
            return _error(str(e), status.HTTP_409_CONFLICT)
        except ValueError as e:
            return _error(str(e), status.HTTP_400_BAD_REQUEST)
        return Response(_timer_state(timer))


class TimerCheckinView(APIView):
    def post(self, request):
        serializer = TimerActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        metric = serializer.validated_data["metric"]
        now = timezone.now()
        # A check-in that arrives after the deadline cannot revive the timer:
        # the absent stretch would end up recorded as study time. Close first,
        # 409, and let the client land on the review banner.
        services.finalize_expired_timer(request.user, metric, now)
        try:
            timer = services.checkin_timer(request.user, metric, now)
        except services.TimerError as e:
            return _error(str(e), status.HTTP_409_CONFLICT)
        return Response(_timer_state(timer))


class TimerExtendView(APIView):
    def post(self, request):
        serializer = ExtendTimerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # Deliberately no finalize here: extending is proof the user is
        # present, and closing the session under their click would be hostile.
        try:
            timer = services.extend_timer(
                request.user, data["metric"], timezone.now(), data["minutes"]
            )
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
        now = timezone.now()
        # A user returning days later and clicking finish must get the
        # truncated auto-close (via 409 + banner), not an inflated record.
        services.finalize_expired_timer(request.user, data["metric"], now)
        try:
            session = services.finish_timer(request.user, data["metric"], now, data["note"])
        except services.TimerError as e:
            return _error(str(e), status.HTTP_409_CONFLICT)
        return Response(SessionSerializer(session).data, status=status.HTTP_201_CREATED)


class SessionListView(APIView):
    def get(self, request):
        metric = request.query_params.get("metric", settings.DEFAULT_SESSION_METRIC)
        services.finalize_expired_timer(request.user, metric, timezone.now())
        limit = int(request.query_params.get("limit", settings.DEFAULT_SESSION_LIMIT))
        rows = Session.objects.filter(user=request.user, metric=metric)
        if request.query_params.get("needs_review"):
            # Oldest first: the review banner resolves them one at a time.
            rows = (
                rows.exclude(close_reason="")
                .filter(reviewed_at__isnull=True)
                .order_by("started_at")
            )
        return Response(SessionSerializer(rows[:limit], many=True).data)

    def post(self, request):
        serializer = ManualSessionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            session = services.log_manual_session(
                request.user,
                data["metric"],
                data["date"],
                data["minutes"],
                timezone.localdate(),
                data["note"],
            )
        except ValueError as e:
            return _error(str(e), status.HTTP_400_BAD_REQUEST)
        return Response(SessionSerializer(session).data, status=status.HTTP_201_CREATED)


class SessionDetailView(APIView):
    def patch(self, request, pk: int):
        serializer = SessionUpdateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            session = services.update_session(
                request.user,
                pk,
                timezone.localdate(),
                day=data.get("date"),
                minutes=data.get("minutes"),
                note=data.get("note"),
            )
        except LookupError as e:
            return _error(str(e), status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return _error(str(e), status.HTTP_400_BAD_REQUEST)
        return Response(SessionSerializer(session).data)

    def delete(self, request, pk: int):
        deleted, _count = Session.objects.filter(user=request.user, pk=pk).delete()
        if not deleted:
            return _error(_("No such session."), status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionReviewView(APIView):
    def post(self, request, pk: int):
        serializer = SessionReviewInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            session = services.review_session(
                request.user,
                pk,
                timezone.now(),
                data["action"],
                ended_at=data["ended_at"],
                note=data["note"] or None,
            )
        except LookupError as e:
            return _error(str(e), status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return _error(str(e), status.HTTP_400_BAD_REQUEST)
        return Response(SessionSerializer(session).data)


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
                request.user,
                data["metric"],
                data["date"],
                data["value"],
                timezone.localdate(),
                data["note"],
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


class PreferencesView(APIView):
    """Per-user preferences (theme accent, open-session reminder)."""

    fields = ["accent_color", "reminder_minutes"]

    def _payload(self, pref: UserPreference) -> dict:
        return {field: getattr(pref, field) for field in self.fields}

    def get(self, request):
        pref, _created = UserPreference.objects.get_or_create(user=request.user)
        return Response(self._payload(pref))

    def put(self, request):
        serializer = PreferencesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pref, _created = UserPreference.objects.get_or_create(user=request.user)
        changed = [f for f in self.fields if f in serializer.validated_data]
        for field in changed:
            setattr(pref, field, serializer.validated_data[field])
        if changed:
            pref.save(update_fields=changed)
        return Response(self._payload(pref))


class StatsView(APIView):
    """Full dashboard payload in a single call."""

    def get(self, request):
        metric_key = request.query_params.get("metric", settings.DEFAULT_SESSION_METRIC)
        weeks = int(request.query_params.get("weeks", settings.DEFAULT_STATS_WEEKS))
        services.finalize_expired_timer(request.user, metric_key, timezone.now())
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
