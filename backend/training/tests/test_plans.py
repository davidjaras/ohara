"""Plan runs: the calendar, adherence and which day is the active one.

The services take `today` explicitly, so none of this needs mocking. The
`run` fixture starts on Monday 2026-08-03 with 2 phases × 2 weeks × 3 days
(Monday / Tuesday / Wednesday), i.e. a 4-week plan of 12 workouts.
"""

from datetime import date, datetime, timezone as tz

import pytest

from training import services
from training.models import ProgramRun, RunStatus, WorkoutDay, WorkoutSession

pytestmark = pytest.mark.django_db

MONDAY_W1 = date(2026, 8, 3)
WEDNESDAY_W1 = date(2026, 8, 5)
MONDAY_W2 = date(2026, 8, 10)
MONDAY_W3 = date(2026, 8, 17)
DONE_AT = datetime(2026, 8, 5, 18, 0, tzinfo=tz.utc)


def day_of(run, phase: int, week: int, order: int) -> WorkoutDay:
    return WorkoutDay.objects.get(
        week__phase__variant=run.variant,
        week__phase__number=phase,
        week__number=week,
        order=order,
    )


def test_start_snaps_any_date_back_to_its_monday(user, plan_access):
    variant = plan_access.variants.get()
    run = services.start_run(user, variant, date(2026, 8, 6), date(2026, 8, 6))
    assert run.started_on == MONDAY_W1


def test_plan_weeks_are_continuous_across_phases(run):
    # Phase 2 week 1 is the third week of the plan, not the first again.
    positions = services.plan_weeks(run.variant)
    assert positions[day_of(run, 1, 1, 1).week_id] == 1
    assert positions[day_of(run, 1, 2, 1).week_id] == 2
    assert positions[day_of(run, 2, 1, 1).week_id] == 3
    assert positions[day_of(run, 2, 2, 1).week_id] == 4


def test_days_land_on_the_weekday_the_coach_wrote(run):
    schedule = {entry["day"].pk: entry for entry in services.run_schedule(run)}

    first_monday = schedule[day_of(run, 1, 1, 1).pk]
    assert first_monday["scheduled_on"] == MONDAY_W1
    assert schedule[day_of(run, 1, 1, 3).pk]["scheduled_on"] == WEDNESDAY_W1
    # Third plan week = phase 2 week 1, two weeks after the start.
    assert schedule[day_of(run, 2, 1, 1).pk]["scheduled_on"] == MONDAY_W3


def test_ends_on_covers_the_last_week_in_full(run):
    assert services.total_weeks(run.variant) == 4
    assert services.run_ends_on(run) == date(2026, 8, 30)  # Sunday of week 4


def test_missing_a_week_never_moves_the_calendar(run, user):
    """Dates hold: adherence drops, the plan's shape does not change."""
    ends_on = services.run_ends_on(run)

    # Week 2 goes by with a single workout done out of three.
    day = day_of(run, 1, 2, 1)
    WorkoutSession.objects.create(
        user=user, run=run, day=day, week_number=2,
        performed_on=MONDAY_W2, completed_at=DONE_AT,
    )

    schedule = services.run_schedule(run)
    numbers = services.adherence(schedule)
    assert numbers["planned"] == 12
    assert numbers["done"] == 1
    assert numbers["weeks"][2] == {"done": 1, "planned": 3}
    assert services.run_ends_on(run) == ends_on


def test_active_day_is_todays_workout_when_it_is_pending(run):
    schedule = services.run_schedule(run)
    entry = services.active_day(schedule, WEDNESDAY_W1, plan_week=1)
    assert entry["day"] == day_of(run, 1, 1, 3)


def test_active_day_catches_up_within_the_current_week(run, user):
    """Wednesday with Monday still unlogged: Monday is the one to open."""
    WorkoutSession.objects.create(
        user=user, run=run, day=day_of(run, 1, 1, 3), week_number=1,
        performed_on=WEDNESDAY_W1, completed_at=DONE_AT,
    )
    schedule = services.run_schedule(run)
    entry = services.active_day(schedule, WEDNESDAY_W1, plan_week=1)
    assert entry["day"] == day_of(run, 1, 1, 1)


def test_active_day_does_not_drag_previous_weeks_along(run, user):
    """Week 1 was missed entirely; in week 2 the plan moves on."""
    schedule = services.run_schedule(run)
    entry = services.active_day(schedule, MONDAY_W2, plan_week=2)
    assert entry["day"] == day_of(run, 1, 2, 1)


def test_active_day_is_the_next_one_on_a_rest_day(run, user):
    """Thursday of week 1: nothing scheduled, so the plan points forward."""
    for order in (1, 2, 3):
        WorkoutSession.objects.create(
            user=user, run=run, day=day_of(run, 1, 1, order), week_number=1,
            performed_on=MONDAY_W1, completed_at=DONE_AT,
        )
    schedule = services.run_schedule(run)
    entry = services.active_day(schedule, date(2026, 8, 6), plan_week=1)
    assert entry["day"] == day_of(run, 1, 2, 1)
    assert entry["scheduled_on"] == MONDAY_W2


def test_current_plan_week_clamps_past_the_end(run):
    assert services.current_plan_week(run, MONDAY_W1) == 1
    assert services.current_plan_week(run, MONDAY_W3) == 3
    assert services.current_plan_week(run, date(2027, 1, 1)) == 4


def test_starting_a_run_abandons_the_previous_one(user, plan_access, glute_coach):
    variant = plan_access.variants.get()
    first = services.start_run(user, variant, MONDAY_W1, MONDAY_W1)

    second = services.start_run(
        user, glute_coach.variants.get(), MONDAY_W3, MONDAY_W3
    )
    first.refresh_from_db()
    assert first.status == RunStatus.ABANDONED
    assert first.ended_on == MONDAY_W3
    assert services.active_run(user) == second
    # The partial unique constraint means exactly one active run per user.
    assert ProgramRun.objects.filter(user=user, status=RunStatus.ACTIVE).count() == 1


def test_reopening_a_day_reuses_its_session(user, run):
    day = day_of(run, 1, 1, 1)
    first, created = services.get_or_create_session(user, day, MONDAY_W1)
    assert created is True

    second, created_again = services.get_or_create_session(user, day, WEDNESDAY_W1)
    assert created_again is False
    assert second.pk == first.pk
    assert second.run_id == run.pk
    assert WorkoutSession.objects.filter(day=day).count() == 1


def test_a_day_outside_the_plan_is_logged_off_plan(user, run, glute_coach):
    """Another program is still trainable; it just does not count for the plan."""
    day = WorkoutDay.objects.get(week__phase__variant__program=glute_coach)
    session, created = services.get_or_create_session(user, day, MONDAY_W1)

    assert created is True
    assert session.run_id is None
    assert services.adherence(services.run_schedule(run))["done"] == 0
