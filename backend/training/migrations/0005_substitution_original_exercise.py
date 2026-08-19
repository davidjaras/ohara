"""Snapshots what a substitution replaced.

Until now a PROGRAM-scoped substitution could only ever apply to the one slot
row it was created on, because slots are per-week: week 2 of the same phase has
different rows. Resolving it across weeks needs a key that survives the
rollover, and the prescribed exercise is half of that key — position alone
would follow a later phase that reuses the same day/order for a different lift.

Existing rows are backfilled from their slot, which is exactly what they
replaced, so they start applying to every week the moment this lands.
"""

import django.db.models.deletion
from django.db import migrations, models


def backfill_original_exercise(apps, schema_editor):
    ExerciseSubstitution = apps.get_model("training", "ExerciseSubstitution")
    for substitution in ExerciseSubstitution.objects.select_related("slot"):
        substitution.original_exercise_id = substitution.slot.exercise_id
        substitution.save(update_fields=["original_exercise"])


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0004_alter_workoutsession_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='exercisesubstitution',
            name='original_exercise',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='substitutions_replacing',
                to='training.exercise',
            ),
        ),
        migrations.RunPython(
            backfill_original_exercise, migrations.RunPython.noop, elidable=True
        ),
        migrations.AlterField(
            model_name='exercisesubstitution',
            name='original_exercise',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='substitutions_replacing',
                to='training.exercise',
            ),
        ),
        migrations.AddIndex(
            model_name='exercisesubstitution',
            index=models.Index(
                fields=['user', 'scope'], name='training_ex_user_id_15ec44_idx'
            ),
        ),
    ]
