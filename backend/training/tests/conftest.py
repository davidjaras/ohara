from datetime import date

import pytest
from rest_framework.test import APIClient

from training.models import (
    Exercise,
    ExerciseSlot,
    Phase,
    Program,
    ProgramAccess,
    ProgramRun,
    ProgramVariant,
    SetPrescription,
    TrainingProfile,
    Week,
    WorkoutDay,
    WorkoutSession,
)

# The real programs name their days MONDAY..SATURDAY and never use Sunday.
WEEKDAY_NAMES = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]

# A Monday, so a run built on it needs no snapping.
PLAN_START = date(2026, 8, 3)


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="ana", password="pw12345")


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(username="beto", password="pw12345")


@pytest.fixture
def client(user) -> APIClient:
    api_client = APIClient()
    api_client.force_authenticate(user)
    return api_client


@pytest.fixture
def other_client(other_user) -> APIClient:
    api_client = APIClient()
    api_client.force_authenticate(other_user)
    return api_client


def build_program(slug: str, phases: int = 1, weeks: int = 1, days: int = 1) -> Program:
    """A minimal but complete tree: program → variant → phase → week → day →
    slot → set. Tests never read the (gitignored) source JSON.

    Defaults stay at one of everything; the scheduling tests ask for a real
    multi-phase plan, which is what makes plan weeks span phases.
    """
    program = Program.objects.create(slug=slug, name=slug.title())
    variant = ProgramVariant.objects.create(
        program=program, slug="default", days_per_week=days
    )
    exercise = Exercise.objects.create(
        slug=f"{slug}-squat",
        name=f"{slug} squat",
        primary_muscle="quads",
        setting="home",
    )
    for phase_number in range(1, phases + 1):
        phase = Phase.objects.create(
            variant=variant,
            number=phase_number,
            label=f"Phase {phase_number}",
            weeks_count=weeks,
        )
        for week_number in range(1, weeks + 1):
            week = Week.objects.create(phase=phase, number=week_number)
            for order in range(1, days + 1):
                day = WorkoutDay.objects.create(
                    week=week,
                    order=order,
                    name=f"Day {order}",
                    day_of_week=WEEKDAY_NAMES[order - 1],
                )
                slot = ExerciseSlot.objects.create(day=day, exercise=exercise, order=1)
                SetPrescription.objects.create(
                    slot=slot, set_number=1, target_reps_min=8, target_reps_max=10,
                    rest_seconds=90, rest_role="between_sets",
                )
    return program


@pytest.fixture
def glute_coach() -> Program:
    return build_program("glute-coach")


@pytest.fixture
def challenge() -> Program:
    return build_program("challenge-2025")


@pytest.fixture
def plan_program() -> Program:
    """2 phases × 2 weeks × 3 days = a 4-week plan of 12 workouts."""
    return build_program("male-method-1", phases=2, weeks=2, days=3)


@pytest.fixture
def enabled_profile(user, glute_coach) -> TrainingProfile:
    """`user` has the module enabled and access to glute_coach only."""
    ProgramAccess.objects.create(user=user, program=glute_coach)
    return TrainingProfile.objects.create(user=user, enabled=True)


@pytest.fixture
def plan_access(user, enabled_profile, plan_program) -> Program:
    ProgramAccess.objects.create(user=user, program=plan_program)
    return plan_program


@pytest.fixture
def run(user, plan_access) -> ProgramRun:
    """An active plan starting on a Monday, so dates are checkable by hand."""
    return ProgramRun.objects.create(
        user=user,
        variant=ProgramVariant.objects.get(program=plan_access),
        started_on=PLAN_START,
    )


@pytest.fixture
def session(user, enabled_profile, glute_coach) -> WorkoutSession:
    day = WorkoutDay.objects.get(
        week__phase__variant__program=glute_coach, order=1
    )
    return WorkoutSession.objects.create(
        user=user, day=day, week_number=1, performed_on=PLAN_START
    )
