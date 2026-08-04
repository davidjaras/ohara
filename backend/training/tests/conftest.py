import pytest
from rest_framework.test import APIClient

from training.models import (
    Equipment,
    Exercise,
    ExerciseSlot,
    Phase,
    Program,
    ProgramAccess,
    ProgramVariant,
    SetPrescription,
    TrainingProfile,
    Week,
    WorkoutDay,
    WorkoutSession,
)


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


def build_program(slug: str) -> Program:
    """A minimal but complete tree: program → variant → phase → week → day →
    slot → set. Tests never read the (gitignored) source JSON."""
    program = Program.objects.create(slug=slug, name=slug.title())
    variant = ProgramVariant.objects.create(program=program, slug="default")
    phase = Phase.objects.create(
        variant=variant, number=1, label="Phase 1", weeks_count=1
    )
    week = Week.objects.create(phase=phase, number=1)
    day = WorkoutDay.objects.create(week=week, order=1, name="Day 1")
    exercise = Exercise.objects.create(
        slug=f"{slug}-squat",
        name=f"{slug} squat",
        primary_muscle="quads",
        setting="home",
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
def enabled_profile(user, glute_coach) -> TrainingProfile:
    """`user` has the module enabled and access to glute_coach only."""
    ProgramAccess.objects.create(user=user, program=glute_coach)
    return TrainingProfile.objects.create(user=user, enabled=True)


@pytest.fixture
def session(user, enabled_profile, glute_coach) -> WorkoutSession:
    day = WorkoutDay.objects.get(
        week__phase__variant__program=glute_coach, order=1
    )
    return WorkoutSession.objects.create(
        user=user, day=day, week_number=1, performed_on="2026-08-03"
    )
