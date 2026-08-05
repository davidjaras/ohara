"""Adds ProgramRun and attaches sessions to it.

`TrainingProfile.active_variant` survives this migration so 0003 can read it
and turn each one into a run; it is dropped there, once the data has moved.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProgramRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('started_on', models.DateField()),
                ('status', models.CharField(choices=[('active', 'Active'), ('completed', 'Completed'), ('abandoned', 'Abandoned')], default='active', max_length=10)),
                ('ended_on', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='program_runs', to=settings.AUTH_USER_MODEL)),
                ('variant', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='training.programvariant')),
            ],
            options={
                'ordering': ['-started_on', '-id'],
            },
        ),
        migrations.AddField(
            model_name='workoutsession',
            name='run',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sessions', to='training.programrun'),
        ),
        migrations.AddConstraint(
            model_name='workoutsession',
            constraint=models.UniqueConstraint(fields=('run', 'day'), name='uniq_run_day'),
        ),
        migrations.AddIndex(
            model_name='programrun',
            index=models.Index(fields=['user', '-started_on'], name='training_pr_user_id_6ee0bb_idx'),
        ),
        migrations.AddConstraint(
            model_name='programrun',
            constraint=models.UniqueConstraint(condition=models.Q(('status', 'active')), fields=('user',), name='uniq_active_run'),
        ),
    ]
