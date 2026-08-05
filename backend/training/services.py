"""Business logic for the training module.

Everything here takes `user` explicitly and returns querysets already scoped
to what that user is allowed to see. Views must never widen these.

Dates are passed in (`today`, `started_on`); only views call
`timezone.localdate()`, so the schedule logic tests without mocks.
"""

from datetime import timedelta

from django.db import models
from django.db.models import Prefetch

from .models import (
    Exercise,
    ExerciseSlot,
    Program,
    ProgramRun,
    ProgramVariant,
    RunStatus,
    SetLog,
    Week,
    WorkoutDay,
    WorkoutSession,
)

# The programs name their days MONDAY..SATURDAY (never Sunday); Ohara counts
# Monday-start ISO weeks everywhere else, so the two line up exactly.
WEEKDAY_OFFSETS = {
    "MONDAY": 0,
    "TUESDAY": 1,
    "WEDNESDAY": 2,
    "THURSDAY": 3,
    "FRIDAY": 4,
    "SATURDAY": 5,
    "SUNDAY": 6,
}


def accessible_programs(user):
    """Layer 2 of access control: never Program.objects.all()."""
    return Program.objects.filter(programaccess__user=user)


def accessible_variants(user):
    return ProgramVariant.objects.filter(program__programaccess__user=user)


def accessible_days(user):
    return WorkoutDay.objects.filter(
        week__phase__variant__program__programaccess__user=user
    )


def accessible_slots(user):
    return ExerciseSlot.objects.filter(
        day__week__phase__variant__program__programaccess__user=user
    )


def own_sessions(user):
    """Layer 3: per-user data is always filtered by owner."""
    return WorkoutSession.objects.filter(user=user)


def own_runs(user):
    return ProgramRun.objects.filter(user=user)


def substitution_candidates(slot):
    """Same-muscle alternatives, grouped by setting, never filtered.

    The picker shows equipment_required on every option: 'home' means
    "needs no gym machine", not "doable today" (8 of the 9 home hamstring
    options need a barbell).
    """
    candidates = (
        Exercise.objects.filter(primary_muscle=slot.exercise.primary_muscle)
        .exclude(pk=slot.exercise_id)
        .prefetch_related("equipment_required")
        .order_by("setting", "name")
    )
    grouped = {"home": [], "gym": []}
    for exercise in candidates:
        grouped[exercise.setting].append(exercise)
    return grouped


# --- Plan scheduling ---------------------------------------------------------


def monday_of(date):
    """The ISO Monday of that date's week. A run always starts on one."""
    return date - timedelta(days=date.weekday())


def variant_weeks(variant):
    """Every week of the variant in the order it is run.

    Ordered by phase then week number rather than summing Phase.weeks_count:
    Glute Coach synthesises its weeks and the declared count could drift from
    the rows that actually exist.
    """
    return (
        Week.objects.filter(phase__variant=variant)
        .order_by("phase__number", "number")
        .select_related("phase")
    )


def total_weeks(variant) -> int:
    return variant_weeks(variant).count()


def plan_weeks(variant) -> dict[int, int]:
    """Week id → its 1-based position in the whole plan (across phases)."""
    return {week.pk: index for index, week in enumerate(variant_weeks(variant), 1)}


def week_offset(day: WorkoutDay) -> int:
    """Days after that week's Monday. Falls back to the slot order when the
    source carries no weekday, which no loaded program does today."""
    named = WEEKDAY_OFFSETS.get(day.day_of_week.strip().upper())
    if named is not None:
        return named
    return min(max(day.order - 1, 0), 6)


def scheduled_date(started_on, plan_week: int, day: WorkoutDay):
    return started_on + timedelta(days=(plan_week - 1) * 7 + week_offset(day))


def run_ends_on(run: ProgramRun):
    """Last day of the last week. Fixed at start: missing workouts never moves
    the calendar (the plan holds its dates and shows adherence instead)."""
    return run.started_on + timedelta(days=total_weeks(run.variant) * 7 - 1)


def active_run(user):
    return own_runs(user).filter(status=RunStatus.ACTIVE).select_related(
        "variant__program"
    ).first()


def start_run(user, variant, started_on, today):
    """Start a plan, abandoning whatever was running before.

    `started_on` is snapped back to its ISO Monday, so week 1 is a real week
    and every day lands on the weekday its coach wrote.
    """
    previous = active_run(user)
    if previous is not None:
        finish_run(previous, today, RunStatus.ABANDONED)
    return ProgramRun.objects.create(
        user=user, variant=variant, started_on=monday_of(started_on)
    )


def finish_run(run: ProgramRun, today, status):
    run.status = status
    run.ended_on = today
    run.save(update_fields=["status", "ended_on"])
    return run


def reschedule_run(run: ProgramRun, started_on):
    run.started_on = monday_of(started_on)
    run.save(update_fields=["started_on"])
    return run


def run_schedule(run: ProgramRun):
    """Every day of the plan with its date, plan week and session (if any).

    One query for the days, one for the sessions — the whole plan is at most a
    few dozen rows (16 weeks × 5 days for the longest program).
    """
    positions = plan_weeks(run.variant)
    days = (
        WorkoutDay.objects.filter(week__phase__variant=run.variant)
        .select_related("week__phase")
        .order_by("week__phase__number", "week__number", "order")
    )
    sessions = {
        session.day_id: session
        for session in WorkoutSession.objects.filter(run=run)
    }
    schedule = []
    for day in days:
        plan_week = positions[day.week_id]
        session = sessions.get(day.pk)
        schedule.append(
            {
                "day": day,
                "plan_week": plan_week,
                "scheduled_on": scheduled_date(run.started_on, plan_week, day),
                "session": session,
                "done": session is not None and session.completed_at is not None,
                "started": session is not None,
            }
        )
    return schedule


def adherence(schedule):
    """Sessions completed vs days planned, overall and per plan week."""
    per_week: dict[int, dict[str, int]] = {}
    for entry in schedule:
        counts = per_week.setdefault(entry["plan_week"], {"done": 0, "planned": 0})
        counts["planned"] += 1
        if entry["done"]:
            counts["done"] += 1
    return {
        "done": sum(week["done"] for week in per_week.values()),
        "planned": sum(week["planned"] for week in per_week.values()),
        "weeks": per_week,
    }


def current_plan_week(run: ProgramRun, today) -> int:
    """1-based, clamped to the plan. Past the end it stays on the last week."""
    elapsed = (today - run.started_on).days
    if elapsed < 0:
        return 1
    return min(elapsed // 7 + 1, max(total_weeks(run.variant), 1))


def active_day(schedule, today, plan_week: int):
    """The day the dashboard should open.

    Today's workout if there is one and it is not finished; otherwise the
    earliest unfinished day *of the current plan week* (catching up on
    Tuesday's session on Wednesday is normal, dragging week 1 along for
    sixteen weeks is not); otherwise the next scheduled day.
    """
    todays = [e for e in schedule if e["scheduled_on"] == today]
    for entry in todays:
        if not entry["done"]:
            return entry

    for entry in schedule:
        if (
            entry["plan_week"] == plan_week
            and entry["scheduled_on"] < today
            and not entry["done"]
        ):
            return entry

    for entry in schedule:
        if entry["scheduled_on"] > today:
            return entry

    return todays[0] if todays else None


def session_for_day(user, day: WorkoutDay, run):
    """The session that the day screen should reopen.

    Inside the active plan a day has exactly one session (uniq_run_day); off
    plan it has whatever was logged, and the most recent one is the useful
    answer.
    """
    if run is not None and day.week.phase.variant_id == run.variant_id:
        return own_sessions(user).filter(run=run, day=day).first()
    return (
        own_sessions(user)
        .filter(run__isnull=True, day=day)
        .order_by(models.F("performed_on").desc(nulls_last=True), "-id")
        .first()
    )


def get_or_create_session(user, day: WorkoutDay, today):
    """Idempotent per (run, day): reopening a day never forks a second session.

    A day outside the active plan is still loggable — it just lands off plan
    (run=None) and never counts toward the plan's adherence.
    """
    run = active_run(user)
    in_plan = run is not None and day.week.phase.variant_id == run.variant_id
    if in_plan:
        session, created = WorkoutSession.objects.get_or_create(
            user=user,
            run=run,
            day=day,
            defaults={
                "week_number": day.week.number,
                "performed_on": today,
            },
        )
        return session, created

    existing = session_for_day(user, day, None)
    if existing is not None:
        return existing, False
    session = WorkoutSession.objects.create(
        user=user,
        run=None,
        day=day,
        week_number=day.week.number,
        performed_on=today,
    )
    return session, True


# --- Exercise history --------------------------------------------------------


def _history_sessions(user, exercise):
    """Sessions in which the user actually performed that exercise.

    Keyed on `performed_exercise`, so a substituted set counts for what was
    done, not for what was prescribed. Imported rows have no `performed_on`,
    so they sort last by date and fall back to insertion order.
    """
    return (
        own_sessions(user)
        .filter(logs__performed_exercise=exercise)
        .distinct()
        .select_related("day")
        .prefetch_related(
            Prefetch(
                "logs",
                queryset=SetLog.objects.filter(performed_exercise=exercise).order_by(
                    "set_number"
                ),
                to_attr="exercise_logs",
            )
        )
        .order_by(models.F("performed_on").desc(nulls_last=True), "-id")
    )


def exercise_history(user, exercise, limit: int = 20):
    return list(_history_sessions(user, exercise)[:limit])


def last_performance(user, exercise, exclude_session=None):
    """The most recent time this exercise was logged, for the "última vez" line."""
    sessions = _history_sessions(user, exercise)
    if exclude_session is not None:
        sessions = sessions.exclude(pk=exclude_session.pk)
    return sessions.first()


def last_performances(user, exercises, exclude_session=None):
    """One lookup per distinct exercise of a day, not one per set.

    A workout day has at most a dozen exercises, so a dict of small queries
    beats a window function nobody can read.
    """
    return {
        exercise.pk: last_performance(user, exercise, exclude_session)
        for exercise in exercises
    }
