import json
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from training.loading import build_exercise_index, expand_prescription, resolve_exercise
from training.models import (
    ExerciseSlot,
    Phase,
    Program,
    ProgramVariant,
    SetPrescription,
    Week,
    WorkoutDay,
)


def _entry_for_week(weekly_prescription: list[dict], week_number: int) -> dict | None:
    """The prescription entry that applies to a given week.

    Glute Coach carries week=null + applies_to_all_weeks=true (the source day
    tables have no week column); everything else declares the week explicitly.
    """
    fallback = None
    for entry in weekly_prescription or []:
        if entry.get("week") == week_number:
            return entry
        if entry.get("week") is None and entry.get("applies_to_all_weeks"):
            fallback = entry
    return fallback


class Command(BaseCommand):
    help = "Load one program JSON into the full hierarchy. Idempotent."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path to a program .json")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be created/updated, writing nothing.",
        )

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")
        data = json.loads(path.read_text())
        source = data.get("program")
        if not source:
            raise CommandError("No 'program' key in the file.")

        index = build_exercise_index()
        if not index:
            raise CommandError(
                "Exercise catalogue is empty - run load_exercise_catalog first."
            )

        with transaction.atomic():
            stats = self._load(source, index)
            if options["dry_run"]:
                transaction.set_rollback(True)
                self.stdout.write("DRY RUN — nothing was written.")
        for model_name, counter in stats.items():
            self.stdout.write(
                f"{model_name}: {counter['created']} created, "
                f"{counter['updated']} updated"
            )

    def _load(self, source: dict, index) -> dict:
        stats: dict[str, Counter] = {
            name: Counter(created=0, updated=0)
            for name in [
                "Program", "ProgramVariant", "Phase", "Week",
                "WorkoutDay", "ExerciseSlot", "SetPrescription",
            ]
        }

        def track(name: str, created: bool):
            stats[name]["created" if created else "updated"] += 1

        program, created = Program.objects.update_or_create(
            slug=source["slug"],
            defaults={"name": source["name"], "coach": source.get("coach") or ""},
        )
        track("Program", created)

        for variant_src in source["variants"]:
            variant, created = ProgramVariant.objects.update_or_create(
                program=program,
                slug=variant_src["slug"],
                defaults={
                    "days_per_week": variant_src.get("days_per_week"),
                    "environment": variant_src.get("environment") or "",
                },
            )
            track("ProgramVariant", created)

            for phase_src in variant_src["phases"]:
                weeks_declared = phase_src.get("weeks_declared_in_day_source", True)
                week_numbers = phase_src.get("weeks") or list(
                    range(1, (phase_src.get("weeks_count") or 1) + 1)
                )
                phase, created = Phase.objects.update_or_create(
                    variant=variant,
                    number=phase_src["number"],
                    defaults={
                        "label": phase_src.get("label") or "",
                        "weeks_count": phase_src.get("weeks_count")
                        or len(week_numbers),
                        "weeks_declared_in_source": weeks_declared,
                        "number_inferred": bool(phase_src.get("number_inferred")),
                        "review_note": phase_src.get("review_note") or "",
                    },
                )
                track("Phase", created)

                for week_number in week_numbers:
                    week, created = Week.objects.update_or_create(
                        phase=phase,
                        number=week_number,
                        defaults={"is_synthesised": not weeks_declared},
                    )
                    track("Week", created)

                    for day_src in phase_src["days"]:
                        if week_number not in (day_src.get("weeks") or week_numbers):
                            continue
                        day, created = WorkoutDay.objects.update_or_create(
                            week=week,
                            order=day_src["order"],
                            defaults={
                                "name": day_src["name"],
                                "day_of_week": day_src.get("day_of_week") or "",
                            },
                        )
                        track("WorkoutDay", created)
                        self._load_slots(day, day_src, week_number, index, track)

        return stats

    def _load_slots(self, day, day_src, week_number, index, track):
        for exercise_src in day_src["exercises"]:
            entry = _entry_for_week(
                exercise_src.get("weekly_prescription"), week_number
            )
            if entry is None:
                continue  # the exercise does not run this week
            exercise = resolve_exercise(index, exercise_src["name"])
            if exercise is None:
                raise CommandError(
                    f"Exercise not in catalogue: {exercise_src['name']!r}"
                )
            slot, created = ExerciseSlot.objects.update_or_create(
                day=day,
                order=exercise_src["order"],
                defaults={
                    "exercise": exercise,
                    "series_label": exercise_src.get("series_label") or "",
                    "series_position": exercise_src.get("series_position"),
                    "coach_annotation": exercise_src.get("annotation") or "",
                    "modifiers": exercise_src.get("modifiers") or [],
                },
            )
            track("ExerciseSlot", created)

            rows = expand_prescription(entry)
            for row in rows:
                set_number = row.pop("set_number")
                _, created = SetPrescription.objects.update_or_create(
                    slot=slot, set_number=set_number, defaults=row
                )
                track("SetPrescription", created)
            # Stale rows from a previous, longer prescription would survive
            # update_or_create; drop them so re-runs converge.
            SetPrescription.objects.filter(
                slot=slot, set_number__gt=len(rows)
            ).delete()
