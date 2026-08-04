import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from training.models import Equipment, Exercise


def humanize(slug: str) -> str:
    return slug.replace("_", " ").capitalize()


class Command(BaseCommand):
    help = "Load exercise-catalog.json (229 exercises + equipment). Idempotent."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path to exercise-catalog.json")
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
        entries = data.get("exercises")
        if not entries:
            raise CommandError("No 'exercises' key in the file.")

        with transaction.atomic():
            stats = self._load(entries)
            if options["dry_run"]:
                transaction.set_rollback(True)
                self.stdout.write("DRY RUN — nothing was written.")
        for line in stats:
            self.stdout.write(line)

    def _load(self, entries) -> list[str]:
        equipment_created = equipment_updated = 0
        slugs = sorted({slug for e in entries for slug in e["equipment_required"] or []})
        by_slug: dict[str, Equipment] = {}
        for slug in slugs:
            equipment, created = Equipment.objects.update_or_create(
                slug=slug, defaults={"name": humanize(slug)}
            )
            by_slug[slug] = equipment
            equipment_created += created
            equipment_updated += not created

        created_count = updated_count = 0
        for entry in entries:
            exercise, created = Exercise.objects.update_or_create(
                slug=entry["slug"],
                defaults={
                    "name": entry["canonical_name"],
                    "name_variants": entry.get("name_variants") or [],
                    "primary_muscle": entry["primary_muscle"],
                    "secondary_muscles": entry.get("secondary_muscles") or [],
                    "movement_pattern": entry.get("movement_pattern") or "",
                    "is_unilateral": bool(entry.get("is_unilateral")),
                    "setting": entry["setting"],
                    "introduced_by_user_substitution": bool(
                        entry.get("introduced_by_user_substitution")
                    ),
                    "exercisedb_id": entry.get("exercisedb_id") or "",
                    "needs_review": entry.get("needs_review") or [],
                },
            )
            exercise.equipment_required.set(
                [by_slug[slug] for slug in entry["equipment_required"] or []]
            )
            created_count += created
            updated_count += not created

        return [
            f"Equipment: {equipment_created} created, {equipment_updated} updated "
            f"({Equipment.objects.count()} total)",
            f"Exercise: {created_count} created, {updated_count} updated "
            f"({Exercise.objects.count()} total)",
        ]
