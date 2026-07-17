"""Attach all tracker data to users.

Adds a nullable user FK to every table, assigns the pre-existing rows to the
app owner's account (created here if missing, with an unusable password to be
set later via `manage.py changepassword`), then makes the FK required and
scopes the uniqueness constraints per user. No rows are deleted.
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

OWNER_USERNAME = "davidjaras"
OWNER_EMAIL = "davidjaras93@gmail.com"

BACKFILLED_MODELS = ["Session", "ActiveTimer", "Measurement", "WeeklyGoal"]


def assign_existing_data(apps, schema_editor):
    tracker_models = [apps.get_model("tracker", name) for name in BACKFILLED_MODELS]
    if not any(model.objects.exists() for model in tracker_models):
        return  # fresh database, nothing to own

    User = apps.get_model("auth", "User")
    owner, _created = User.objects.get_or_create(
        username=OWNER_USERNAME,
        defaults={
            "email": OWNER_EMAIL,
            "is_staff": True,
            "is_superuser": True,
            "password": "!",  # unusable until set via changepassword
        },
    )
    for model in tracker_models:
        model.objects.filter(user__isnull=True).update(user=owner)


class Migration(migrations.Migration):
    dependencies = [
        ("tracker", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="session",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sessions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="activetimer",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="active_timers",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="measurement",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="measurements",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="weeklygoal",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="weekly_goals",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(assign_existing_data, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="session",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sessions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="activetimer",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="active_timers",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="measurement",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="measurements",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="weeklygoal",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="weekly_goals",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # Uniqueness now scoped per user.
        migrations.RemoveConstraint(
            model_name="weeklygoal",
            name="unique_goal_per_week",
        ),
        migrations.AddConstraint(
            model_name="weeklygoal",
            constraint=models.UniqueConstraint(
                fields=["user", "metric", "week_start"], name="unique_goal_per_user_week"
            ),
        ),
        migrations.AlterField(
            model_name="activetimer",
            name="metric",
            field=models.CharField(max_length=50),
        ),
        migrations.AddConstraint(
            model_name="activetimer",
            constraint=models.UniqueConstraint(
                fields=["user", "metric"], name="unique_timer_per_user_metric"
            ),
        ),
    ]
