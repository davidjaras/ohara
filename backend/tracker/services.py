"""Business logic: timer, aggregations, goals and streak.

Every function is scoped to a `user` and takes an explicit `now` (aware
datetime) or `today` (local date) so the logic is deterministic and testable
without mocks. Views pass request.user and timezone.now() / localdate().
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .metrics import Metric, get_measurement_metric, get_session_metric
from .models import ActiveTimer, Measurement, Session, WeeklyGoal


class TimerError(Exception):
    """Invalid timer operation (already running, none active, etc.)."""


# --- Weeks -------------------------------------------------------------------

def week_start(day: date) -> date:
    """Monday of the ISO week `day` belongs to."""
    return day - timedelta(days=day.weekday())


def local_date(dt: datetime) -> date:
    """Local day (per TIME_ZONE) of an aware datetime."""
    return timezone.localtime(dt).date()


# --- Timer -------------------------------------------------------------------

def start_timer(user, metric_key: str, now: datetime) -> ActiveTimer:
    get_session_metric(metric_key)
    if ActiveTimer.objects.filter(user=user, metric=metric_key).exists():
        raise TimerError(_("There is already a session in progress for this metric."))
    return ActiveTimer.objects.create(
        user=user, metric=metric_key, started_at=now, running_since=now
    )


def _get_timer(user, metric_key: str) -> ActiveTimer:
    try:
        return ActiveTimer.objects.get(user=user, metric=metric_key)
    except ActiveTimer.DoesNotExist:
        raise TimerError(_("There is no session in progress."))


def pause_timer(user, metric_key: str, now: datetime) -> ActiveTimer:
    timer = _get_timer(user, metric_key)
    if timer.is_paused:
        raise TimerError(_("The session is already paused."))
    timer.accumulated_seconds = timer.elapsed_seconds(now)
    timer.running_since = None
    timer.save(update_fields=["accumulated_seconds", "running_since"])
    return timer


def resume_timer(user, metric_key: str, now: datetime) -> ActiveTimer:
    timer = _get_timer(user, metric_key)
    if not timer.is_paused:
        raise TimerError(_("The session is not paused."))
    timer.running_since = now
    timer.save(update_fields=["running_since"])
    return timer


@transaction.atomic
def finish_timer(user, metric_key: str, now: datetime, note: str = "") -> Session:
    """Close the timer and create the Session, attributed to the start day."""
    timer = _get_timer(user, metric_key)
    session = Session.objects.create(
        user=user,
        metric=metric_key,
        date=local_date(timer.started_at),
        duration_seconds=timer.elapsed_seconds(now),
        note=note,
        started_at=timer.started_at,
        ended_at=now,
    )
    timer.delete()
    return session


def discard_timer(user, metric_key: str) -> None:
    _get_timer(user, metric_key).delete()


# --- Manual entry ------------------------------------------------------------

def log_manual_session(user, metric_key: str, day: date, minutes: int, note: str = "") -> Session:
    get_session_metric(metric_key)
    if minutes <= 0:
        raise ValueError(_("Minutes must be greater than zero."))
    return Session.objects.create(
        user=user, metric=metric_key, date=day, duration_seconds=minutes * 60, note=note
    )


# --- Goals -------------------------------------------------------------------

def goal_for_week(user, metric: Metric, week: date) -> int:
    """Goal (minutes) in effect for the week starting at `week`."""
    row = (
        WeeklyGoal.objects.filter(user=user, metric=metric.key, week_start__lte=week)
        .order_by("-week_start")
        .first()
    )
    if row is not None:
        return row.minutes
    return metric.default_weekly_goal_minutes or 0


def set_goal(user, metric_key: str, minutes: int, today: date) -> WeeklyGoal:
    """Set the goal from the current week onward (past weeks are untouched)."""
    get_session_metric(metric_key)
    if minutes <= 0:
        raise ValueError(_("The goal must be greater than zero."))
    row, _created = WeeklyGoal.objects.update_or_create(
        user=user,
        metric=metric_key,
        week_start=week_start(today),
        defaults={"minutes": minutes},
    )
    # A goal row later than the current week would shadow the new value. The
    # normal flow never writes future rows, but clean them up for hygiene.
    WeeklyGoal.objects.filter(
        user=user, metric=metric_key, week_start__gt=row.week_start
    ).delete()
    return row


# --- Aggregations ------------------------------------------------------------

def daily_minutes(user, metric_key: str, start: date, end: date) -> list[dict]:
    """Minutes per day within [start, end], including zero days."""
    totals = dict(
        Session.objects.filter(user=user, metric=metric_key, date__gte=start, date__lte=end)
        .values_list("date")
        .annotate(total=Sum("duration_seconds"))
        .values_list("date", "total")
    )
    days = []
    day = start
    while day <= end:
        days.append({"date": day, "minutes": (totals.get(day, 0) or 0) // 60})
        day += timedelta(days=1)
    return days


def week_cumulative(user, metric_key: str, today: date) -> list[dict]:
    """Cumulative minutes for the current ISO week, Monday through `today`.

    Days without sessions keep the previous value (flat line). Future days
    are not included: the series deliberately stops at `today`.
    """
    get_session_metric(metric_key)
    days = daily_minutes(user, metric_key, week_start(today), today)
    cumulative = 0
    out = []
    for day in days:
        cumulative += day["minutes"]
        out.append(
            {"date": day["date"], "minutes": day["minutes"], "cumulative_minutes": cumulative}
        )
    return out


@dataclass
class WeekSummary:
    week_start: date
    minutes: int
    goal_minutes: int
    met: bool


def _week_seconds(user, metric_key: str) -> dict[date, int]:
    """Total seconds per week (only weeks that have data)."""
    totals: dict[date, int] = {}
    rows = (
        Session.objects.filter(user=user, metric=metric_key)
        .values_list("date")
        .annotate(total=Sum("duration_seconds"))
        .values_list("date", "total")
    )
    for day, seconds in rows:
        week = week_start(day)
        totals[week] = totals.get(week, 0) + (seconds or 0)
    return totals


def week_summary(user, metric: Metric, week: date, week_seconds: dict[date, int]) -> WeekSummary:
    seconds = week_seconds.get(week, 0)
    goal = goal_for_week(user, metric, week)
    return WeekSummary(
        week_start=week,
        minutes=seconds // 60,
        goal_minutes=goal,
        met=goal > 0 and seconds >= goal * 60,
    )


def weekly_summaries(user, metric_key: str, today: date, weeks: int) -> list[WeekSummary]:
    """Summaries for the last `weeks` weeks, current included, ascending."""
    metric = get_session_metric(metric_key)
    totals = _week_seconds(user, metric_key)
    current = week_start(today)
    return [
        week_summary(user, metric, current - timedelta(weeks=i), totals)
        for i in range(weeks - 1, -1, -1)
    ]


def current_streak(user, metric_key: str, today: date) -> int:
    """Consecutive weeks that met their goal.

    The current week counts only once its goal is met; while unfinished it
    does not break the streak. Going backwards, the streak stops at the first
    week that missed its goal.
    """
    metric = get_session_metric(metric_key)
    totals = _week_seconds(user, metric_key)
    current = week_start(today)

    streak = 0
    if week_summary(user, metric, current, totals).met:
        streak += 1
    week = current - timedelta(weeks=1)
    # Weeks before the first recorded data never meet the goal, so the walk
    # terminates naturally; no extra bound needed.
    while week_summary(user, metric, week, totals).met:
        streak += 1
        week -= timedelta(weeks=1)
    return streak


def total_minutes(user, metric_key: str) -> int:
    seconds = (
        Session.objects.filter(user=user, metric=metric_key).aggregate(
            total=Sum("duration_seconds")
        )["total"]
        or 0
    )
    return seconds // 60


# --- Measurements ------------------------------------------------------------

def log_measurement(user, metric_key: str, day: date, value, note: str = "") -> Measurement:
    get_measurement_metric(metric_key)
    return Measurement.objects.create(
        user=user, metric=metric_key, date=day, value=value, note=note
    )
