"""Business logic for the training module.

Everything here takes `user` explicitly and returns querysets already scoped
to what that user is allowed to see. Views must never widen these.
"""

from .models import Exercise, ExerciseSlot, Program, ProgramVariant, WorkoutDay, WorkoutSession


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
