"""Business logic: timer, aggregations, goals and streak.

Every function is scoped to a `user` and takes an explicit `now` (aware
datetime) or `today` (local date) so the logic is deterministic and testable
without mocks. Views pass request.user and timezone.now() / localdate().
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Sum
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


def _local_midnight(day: date) -> datetime:
    """Start of `day` in the local timezone."""
    return datetime.combine(day, time.min, tzinfo=timezone.get_current_timezone())


def format_minutes(total_minutes: int) -> str:
    """Human-readable duration, mirroring the frontend's formatMinutes."""
    hours, minutes = divmod(total_minutes, 60)
    if hours == 0:
        return f"{minutes} min"
    if minutes == 0:
        return f"{hours} h"
    return f"{hours} h {minutes} min"


# --- Timer -------------------------------------------------------------------

def start_timer(
    user, metric_key: str, now: datetime, planned_minutes: int | None = None
) -> ActiveTimer:
    get_session_metric(metric_key)
    if planned_minutes is not None and not 1 <= planned_minutes <= settings.MAX_DAY_MINUTES:
        raise ValueError(
            _("The planned duration must be between 1 and %(max)d minutes.")
            % {"max": settings.MAX_DAY_MINUTES}
        )
    if ActiveTimer.objects.filter(user=user, metric=metric_key).exists():
        raise TimerError(_("There is already a session in progress for this metric."))
    return ActiveTimer.objects.create(
        user=user,
        metric=metric_key,
        started_at=now,
        running_since=now,
        planned_duration_seconds=None if planned_minutes is None else planned_minutes * 60,
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
    """Close the timer and create the Session.

    `date` is the day the session started; the time is attributed to the days
    it actually spans when aggregating (see `day_segments`). A timer left
    running for days is clamped to a full day from its start instead of
    writing an impossible session.
    """
    timer = _get_timer(user, metric_key)
    elapsed = timer.elapsed_seconds(now)
    ended_at = now
    max_seconds = settings.MAX_DAY_MINUTES * 60
    if elapsed > max_seconds:
        elapsed = max_seconds
        ended_at = timer.started_at + timedelta(seconds=max_seconds)
    session = Session.objects.create(
        user=user,
        metric=metric_key,
        date=local_date(timer.started_at),
        duration_seconds=elapsed,
        note=note,
        started_at=timer.started_at,
        ended_at=ended_at,
    )
    timer.delete()
    return session


def extend_timer(user, metric_key: str, now: datetime, minutes: int) -> ActiveTimer:
    """Push a planned session's target further out.

    A duration goal must not become a ceiling that cuts a productive session
    short: extending costs one action and the countdown simply continues.
    """
    timer = _get_timer(user, metric_key)
    if timer.planned_duration_seconds is None:
        raise TimerError(_("Only sessions with a planned duration can be extended."))
    if minutes <= 0:
        raise ValueError(_("Minutes must be greater than zero."))
    new_planned = timer.planned_duration_seconds + minutes * 60
    if new_planned > settings.MAX_DAY_MINUTES * 60:
        raise ValueError(
            _("A session cannot be longer than a day (%(max)d minutes).")
            % {"max": settings.MAX_DAY_MINUTES}
        )
    timer.planned_duration_seconds = new_planned
    timer.save(update_fields=["planned_duration_seconds"])
    return timer


def discard_timer(user, metric_key: str) -> None:
    _get_timer(user, metric_key).delete()


# --- Auto-close and repair ---------------------------------------------------

@transaction.atomic
def finalize_expired_timer(user, metric_key: str, now: datetime) -> Session | None:
    """Close a timer whose deadline has passed, judging from timestamps alone.

    There is no background process: every view that can observe a timer calls
    this first, so an expired timer becomes a session on the next request,
    whenever that arrives. A planned session that outlived its grace is closed
    at exactly the planned duration. Paused timers never expire: paused time
    accrues nothing, so a forgotten pause cannot inflate any record.
    """
    timer = (
        ActiveTimer.objects.select_for_update()
        .filter(user=user, metric=metric_key)
        .first()
    )
    if timer is None or timer.is_paused or timer.planned_duration_seconds is None:
        return None
    planned = timer.planned_duration_seconds
    if timer.elapsed_seconds(now) < planned + settings.TIMER_GRACE_SECONDS:
        return None
    # The instant the running clock crossed the planned mark. If the crossing
    # happened in an earlier running segment this lands slightly late, but the
    # recorded duration is the planned one either way.
    ended_at = timer.running_since + timedelta(
        seconds=max(0, planned - timer.accumulated_seconds)
    )
    session = Session.objects.create(
        user=user,
        metric=timer.metric,
        date=local_date(timer.started_at),
        duration_seconds=planned,
        started_at=timer.started_at,
        ended_at=ended_at,
        close_reason=Session.CLOSE_PLANNED_END,
        estimated_duration_seconds=planned,
    )
    timer.delete()
    return session


@transaction.atomic
def review_session(
    user,
    session_id: int,
    now: datetime,
    action: str,
    ended_at: datetime | None = None,
    note: str | None = None,
) -> Session:
    """Resolve an auto-closed session: keep the estimate or correct its end.

    Adjusting keeps the real start and recomputes the duration from the new
    end. The original estimate stays frozen in `estimated_duration_seconds`,
    so the size of the correction can be measured later.
    """
    try:
        session = Session.objects.select_for_update().get(user=user, pk=session_id)
    except Session.DoesNotExist:
        raise LookupError(_("No such session."))
    if not session.needs_review:
        raise ValueError(_("This session is not pending review."))
    if action == "adjust":
        if ended_at is None:
            raise ValueError(_("An end time is required to adjust the session."))
        if session.started_at is None or ended_at <= session.started_at:
            raise ValueError(_("The end must be after the start."))
        if ended_at > now:
            raise ValueError(_("The end cannot be in the future."))
        duration = int((ended_at - session.started_at).total_seconds())
        if duration > settings.MAX_DAY_MINUTES * 60:
            raise ValueError(
                _("A session cannot be longer than a day (%(max)d minutes).")
                % {"max": settings.MAX_DAY_MINUTES}
            )
        session.ended_at = ended_at
        session.duration_seconds = duration
    if note:
        session.note = note
    session.reviewed_at = now
    session.save()
    return session


# --- Day attribution ---------------------------------------------------------

def day_segments(session: Session) -> list[tuple[date, int]]:
    """Seconds of `session` attributable to each local day it spans.

    Manual entries carry no timestamps, so everything lands on their date. A
    timed session is split at local midnight: a session from 23:30 to 00:30
    gives half an hour to each day.

    The split is proportional to the wall-clock time spent on each day, not a
    slice of the interval: `duration_seconds` excludes pauses, so it does not
    match `ended_at - started_at`. Where the pauses fell is not recorded, and
    spreading them evenly is the fairest simple rule. The remainder goes to
    the last day, so the parts always add up to `duration_seconds` exactly.
    """
    total = session.duration_seconds
    if session.started_at is None or session.ended_at is None:
        return [(session.date, total)]

    start = timezone.localtime(session.started_at)
    end = timezone.localtime(session.ended_at)
    wall = (end - start).total_seconds()
    if wall <= 0 or start.date() == end.date():
        return [(start.date(), total)]

    # Wall-clock seconds per local day.
    shares: list[tuple[date, float]] = []
    cursor = start
    while cursor < end:
        chunk_end = min(_local_midnight(cursor.date() + timedelta(days=1)), end)
        shares.append((cursor.date(), (chunk_end - cursor).total_seconds()))
        cursor = chunk_end

    segments = []
    allocated = 0
    for day, seconds in shares[:-1]:
        part = int(total * seconds / wall)
        segments.append((day, part))
        allocated += part
    segments.append((shares[-1][0], total - allocated))
    return segments


def _sessions_overlapping(user, metric_key: str, start: date, end: date):
    """Sessions that can contribute time to [start, end].

    A timed session that began before `start` may still reach into the range,
    so it cannot be filtered by `date` alone.
    """
    return Session.objects.filter(user=user, metric=metric_key, date__lte=end).filter(
        Q(ended_at__isnull=True, date__gte=start) | Q(ended_at__gte=_local_midnight(start))
    )


def _seconds_by_day(
    user, metric_key: str, start: date, end: date, exclude_id: int | None = None
) -> dict[date, int]:
    """Seconds attributable to each day in [start, end] (days with data only)."""
    totals: dict[date, int] = {}
    for session in _sessions_overlapping(user, metric_key, start, end):
        if session.pk == exclude_id:
            continue
        for day, seconds in day_segments(session):
            if start <= day <= end:
                totals[day] = totals.get(day, 0) + seconds
    return totals


def day_seconds(user, metric_key: str, day: date, exclude_id: int | None = None) -> int:
    """Seconds already logged on `day`, optionally ignoring one session."""
    return _seconds_by_day(user, metric_key, day, day, exclude_id).get(day, 0)


# --- Manual entry ------------------------------------------------------------

def _validate_manual_entry(
    user, metric_key: str, day: date, minutes: int, today: date, exclude_id: int | None = None
) -> None:
    """Guards shared by creating and editing a manual entry."""
    max_minutes = settings.MAX_DAY_MINUTES
    if minutes <= 0:
        raise ValueError(_("Minutes must be greater than zero."))
    if minutes > max_minutes:
        raise ValueError(
            _("A session cannot be longer than a day (%(max)d minutes).") % {"max": max_minutes}
        )
    if day > today:
        raise ValueError(_("The date cannot be in the future."))
    used = day_seconds(user, metric_key, day, exclude_id)
    free = max_minutes * 60 - used
    if minutes * 60 > free:
        raise ValueError(
            _("That day already has %(used)s logged; only %(free)s more fit.")
            % {"used": format_minutes(used // 60), "free": format_minutes(free // 60)}
        )


def log_manual_session(
    user, metric_key: str, day: date, minutes: int, today: date, note: str = ""
) -> Session:
    get_session_metric(metric_key)
    _validate_manual_entry(user, metric_key, day, minutes, today)
    return Session.objects.create(
        user=user, metric=metric_key, date=day, duration_seconds=minutes * 60, note=note
    )


@transaction.atomic
def update_session(
    user,
    session_id: int,
    today: date,
    day: date | None = None,
    minutes: int | None = None,
    note: str | None = None,
) -> Session:
    """Edit an existing session. Only the given fields change.

    Rewriting the date or the duration of a timed session makes its
    start/end timestamps a lie, so they are dropped: the row becomes a
    corrected manual entry, which is what it now is. Editing only the note
    keeps them.
    """
    try:
        session = Session.objects.select_for_update().get(user=user, pk=session_id)
    except Session.DoesNotExist:
        raise LookupError(_("No such session."))

    retimed = day is not None or minutes is not None
    if retimed:
        new_day = day if day is not None else session.date
        new_minutes = minutes if minutes is not None else session.duration_seconds // 60
        _validate_manual_entry(
            user, session.metric, new_day, new_minutes, today, exclude_id=session.pk
        )
        session.date = new_day
        session.duration_seconds = new_minutes * 60
        session.started_at = None
        session.ended_at = None
    if note is not None:
        session.note = note
    session.save()
    return session


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
    if minutes > settings.MAX_WEEK_MINUTES:
        raise ValueError(
            _("The goal cannot exceed the %(max)d minutes a week has.")
            % {"max": settings.MAX_WEEK_MINUTES}
        )
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
    totals = _seconds_by_day(user, metric_key, start, end)
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
    """Total seconds per week (only weeks that have data).

    Buckets by the day each segment belongs to, so a session that runs from
    Sunday night into Monday is split across the two weeks as well.
    """
    totals: dict[date, int] = {}
    for session in Session.objects.filter(user=user, metric=metric_key):
        for day, seconds in day_segments(session):
            week = week_start(day)
            totals[week] = totals.get(week, 0) + seconds
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

def log_measurement(
    user, metric_key: str, day: date, value, today: date, note: str = ""
) -> Measurement:
    get_measurement_metric(metric_key)
    if day > today:
        raise ValueError(_("The date cannot be in the future."))
    return Measurement.objects.create(
        user=user, metric=metric_key, date=day, value=value, note=note
    )
