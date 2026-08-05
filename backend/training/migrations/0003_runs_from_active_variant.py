"""Turns each `TrainingProfile.active_variant` into a real ProgramRun.

Picking a program used to be a label with no dates. Every profile that had one
becomes an active run backdated to the Monday of that user's first session for
the variant, so an in-flight program keeps its history instead of restarting.

It also repairs the duplicate sessions the old lazy-create left behind. Until
now every visit to a day created its own `WorkoutSession` on the first logged
set, so one workout could be spread over several rows — the dev database has
four for 2026-08-04, two of them empty and two holding the same set twice.
Left alone they would make the new exercise history list one workout several
times, so same-day duplicates are merged into one session:

* the richest row (most logs, then most recent) keeps the workout;
* logs for a set it does not already have move onto it;
* rows left with nothing are deleted.

Nothing that was actually recorded is lost — only repeats of a set already
present on the keeper — but the merge cannot be undone, so the reverse only
restores `active_variant` and detaches the runs.

Imported history (`imported_from` set, no `performed_on`) is never touched and
stays off plan.
"""

from datetime import timedelta

from django.db import migrations
from django.db.models import Count
from django.utils import timezone


def monday_of(date):
    return date - timedelta(days=date.weekday())


def merge_duplicate_sessions(WorkoutSession, SetLog):
    """One workout per (user, day, date). Different dates stay separate: that
    is the same day trained twice, not the bug."""
    groups = (
        WorkoutSession.objects.filter(imported_from="")
        .exclude(performed_on=None)
        .values("user_id", "day_id", "performed_on")
        .annotate(rows=Count("id"))
        .filter(rows__gt=1)
    )
    for group in groups:
        duplicates = list(
            WorkoutSession.objects.filter(
                user_id=group["user_id"],
                day_id=group["day_id"],
                performed_on=group["performed_on"],
                imported_from="",
            )
            .annotate(log_count=Count("logs"))
            .order_by("-log_count", "-id")
        )
        keeper, losers = duplicates[0], duplicates[1:]
        seen = set(keeper.logs.values_list("prescription_id", "set_number"))
        for loser in losers:
            for log in loser.logs.all():
                key = (log.prescription_id, log.set_number)
                if key in seen:
                    continue
                seen.add(key)
                SetLog.objects.filter(pk=log.pk).update(session=keeper)
            # Whatever is left is a repeat of a set the keeper already has.
            loser.logs.all().delete()
            loser.delete()


def create_runs(apps, schema_editor):
    TrainingProfile = apps.get_model("training", "TrainingProfile")
    ProgramRun = apps.get_model("training", "ProgramRun")
    WorkoutSession = apps.get_model("training", "WorkoutSession")
    SetLog = apps.get_model("training", "SetLog")
    today = timezone.localdate()

    merge_duplicate_sessions(WorkoutSession, SetLog)

    profiles = TrainingProfile.objects.exclude(active_variant=None).select_related(
        "active_variant"
    )
    for profile in profiles:
        variant = profile.active_variant
        sessions = WorkoutSession.objects.filter(
            user_id=profile.user_id, day__week__phase__variant=variant
        ).exclude(performed_on=None)

        first = sessions.order_by("performed_on", "id").first()
        started_on = monday_of(first.performed_on if first else today)
        run = ProgramRun.objects.create(
            user_id=profile.user_id,
            variant=variant,
            started_on=started_on,
            status="active",
        )
        # After the merge there is at most one session per day, so uniq_run_day
        # holds without picking a winner here.
        sessions.update(run=run)


def drop_runs(apps, schema_editor):
    """Reverse: put the active variant back on the profile and detach.

    The session merge is not reversed — the duplicate rows are gone.
    """
    TrainingProfile = apps.get_model("training", "TrainingProfile")
    ProgramRun = apps.get_model("training", "ProgramRun")
    WorkoutSession = apps.get_model("training", "WorkoutSession")

    for run in ProgramRun.objects.filter(status="active"):
        TrainingProfile.objects.filter(user_id=run.user_id).update(
            active_variant=run.variant_id
        )
    WorkoutSession.objects.exclude(run=None).update(run=None)
    ProgramRun.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0002_programrun"),
    ]

    operations = [
        migrations.RunPython(create_runs, drop_runs),
        migrations.RemoveField(
            model_name="trainingprofile",
            name="active_variant",
        ),
    ]
