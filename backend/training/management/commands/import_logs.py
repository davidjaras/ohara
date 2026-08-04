import json
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from training.loading import build_exercise_index, resolve_exercise
from training.models import (
    ExerciseSlot,
    Phase,
    SetLog,
    SetPrescription,
    WeightBasis,
    WorkoutDay,
    WorkoutSession,
)

UNDECLARED_BASIS_NOTE = (
    "weight_basis undeclared in source; assumed total"
)


class Command(BaseCommand):
    help = (
        "Import historical set logs from a program JSON (only male-method-1 "
        "carries any). Re-runnable: the batch is deleted and re-created."
    )

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path to a program .json with logs")
        parser.add_argument(
            "--user",
            required=True,
            help="Username that owns the imported sessions. Required: the "
            "logs are personal data and need an owner.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be imported, writing nothing.",
        )

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")
        user = get_user_model().objects.filter(username=options["user"]).first()
        if user is None:
            raise CommandError(f"User not found: {options['user']!r}")

        data = json.loads(path.read_text())
        source = data.get("program")
        if not source:
            raise CommandError("No 'program' key in the file.")
        program_slug = source["slug"]
        batch_tag = f"{program_slug}-import"

        index = build_exercise_index()

        with transaction.atomic():
            # Historical rows carry no source ID; the batch tag is the
            # deduplication key. Delete-and-recreate keeps re-runs convergent.
            deleted_sessions = WorkoutSession.objects.filter(
                user=user, imported_from=batch_tag
            ).delete()
            stats = self._import(source, user, batch_tag, index)
            if options["dry_run"]:
                transaction.set_rollback(True)
                self.stdout.write("DRY RUN — nothing was written.")

        self.stdout.write(f"Replaced previous batch: {deleted_sessions[0]} rows")
        for line in stats:
            self.stdout.write(line)

    def _import(self, source, user, batch_tag, index) -> list[str]:
        entries = set_logs = substituted = 0
        sessions: dict[tuple, WorkoutSession] = {}

        for variant_src in source["variants"]:
            for phase_src in variant_src["phases"]:
                phase = Phase.objects.get(
                    variant__program__slug=source["slug"],
                    variant__slug=variant_src["slug"],
                    number=phase_src["number"],
                )
                for day_src in phase_src["days"]:
                    for exercise_src in day_src["exercises"]:
                        for log in exercise_src.get("logs") or []:
                            entries += 1
                            counts = self._import_entry(
                                log, exercise_src, day_src, phase,
                                user, batch_tag, index, sessions,
                            )
                            set_logs += counts[0]
                            substituted += counts[1]

        return [
            f"Log entries: {entries}",
            f"WorkoutSession: {len(sessions)} created",
            f"SetLog: {set_logs} created ({substituted} substituted)",
        ]

    def _import_entry(
        self, log, exercise_src, day_src, phase, user, batch_tag, index, sessions
    ) -> tuple[int, int]:
        week_number = log["week"]
        day = WorkoutDay.objects.get(
            week__phase=phase, week__number=week_number, order=day_src["order"]
        )
        key = (day.pk,)
        if key not in sessions:
            # The source carries no real dates: performed_on stays null
            # rather than inventing a plausible date unmarked.
            sessions[key] = WorkoutSession.objects.create(
                user=user,
                day=day,
                week_number=week_number,
                performed_on=None,
                imported_from=batch_tag,
            )
        session = sessions[key]

        slot = ExerciseSlot.objects.get(day=day, order=exercise_src["order"])
        substitution = log.get("substitution")
        if substitution:
            performed = resolve_exercise(
                index, substitution["performed_exercise_name"]
            )
            if performed is None:
                raise CommandError(
                    "Substituted exercise not in catalogue: "
                    f"{substitution['performed_exercise_name']!r}"
                )
        else:
            performed = slot.exercise

        notes = [note for note in [log.get("note")] if note]
        created = substituted_count = 0
        for set_src in log.get("sets") or []:
            weight_info = set_src.get("weight") or {}
            weight_value = weight_info.get("value")
            basis, basis_note = self._weight_basis(log, weight_info)
            import_notes = notes + ([basis_note] if basis_note else [])
            SetLog.objects.create(
                session=session,
                prescription=SetPrescription.objects.filter(
                    slot=slot, set_number=set_src["set_number"]
                ).first(),
                performed_exercise=performed,
                was_substituted=bool(substitution),
                set_number=set_src["set_number"],
                weight=(
                    Decimal(str(weight_value)) if weight_value is not None else None
                ),
                weight_basis=basis,
                reps=(set_src.get("reps") or {}).get("value"),
                imported_from=batch_tag,
                import_note="; ".join(import_notes),
            )
            created += 1
            substituted_count += bool(substitution)
        return created, substituted_count

    @staticmethod
    def _weight_basis(log, weight_info) -> tuple[str, str]:
        if weight_info.get("bodyweight"):
            # Bodyweight rows never carry a numeric value in this data.
            return WeightBasis.BODYWEIGHT, ""
        declared = log.get("weight_basis")
        if declared == "per_dumbbell":
            return WeightBasis.PER_DUMBBELL, ""
        if declared == "total":
            return WeightBasis.TOTAL, ""
        return WeightBasis.TOTAL, UNDECLARED_BASIS_NOTE
