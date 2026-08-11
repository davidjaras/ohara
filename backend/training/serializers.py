from rest_framework import serializers

from .models import (
    Exercise,
    ExerciseSlot,
    ExerciseSubstitution,
    Phase,
    Program,
    ProgramRun,
    ProgramVariant,
    RunStatus,
    SetLog,
    SetPrescription,
    Week,
    WorkoutDay,
    WorkoutSession,
)


class ExerciseSerializer(serializers.ModelSerializer):
    equipment_required = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name"
    )

    class Meta:
        model = Exercise
        fields = [
            "id", "slug", "name", "primary_muscle", "secondary_muscles",
            "movement_pattern", "equipment_required", "is_unilateral", "setting",
        ]


class SetPrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SetPrescription
        fields = [
            "id", "set_number", "target_reps_min", "target_reps_max",
            "to_failure", "hold_seconds", "reps_per_side", "rest_seconds",
            "rest_role", "tempo", "is_backoff_set", "cluster_reps", "reps_raw",
        ]


class PerformanceSerializer(serializers.ModelSerializer):
    """One past session, reduced to the sets of a single exercise.

    Feeds both the "última vez" line on the day screen and the full history
    dialog, so they can never disagree. `exercise_logs` is the prefetch
    services._history_sessions attaches.
    """

    day_name = serializers.CharField(source="day.name", read_only=True)
    program = serializers.CharField(
        source="day.week.phase.variant.program.name", read_only=True
    )
    sets = serializers.SerializerMethodField()

    class Meta:
        model = WorkoutSession
        fields = ["id", "performed_on", "day_name", "program", "sets"]

    def get_sets(self, session):
        logs = getattr(session, "exercise_logs", None)
        if logs is None:
            logs = session.logs.all()
        return [
            {
                "set_number": log.set_number,
                # A string, like SetLogSerializer's DecimalField: the two shapes
                # end up side by side in the same UI row.
                "weight": None if log.weight is None else str(log.weight),
                "weight_basis": log.weight_basis,
                "reps": log.reps,
                "was_substituted": log.was_substituted,
            }
            for log in logs
        ]


class ExerciseSlotSerializer(serializers.ModelSerializer):
    # `exercise` stays the prescription — what the coach wrote. What is being
    # done is `substitution.replacement` when there is one, which is what the
    # card is titled by and what a logged set records.
    exercise = ExerciseSerializer(read_only=True)
    sets = SetPrescriptionSerializer(many=True, read_only=True)
    substitution = serializers.SerializerMethodField()
    # Filled by DayDetailView from a single lookup per exercise; None when the
    # exercise has never been logged.
    last_performance = serializers.SerializerMethodField()

    class Meta:
        model = ExerciseSlot
        fields = [
            "id", "order", "series_label", "series_position", "is_superset",
            "coach_annotation", "modifiers", "exercise", "sets",
            "substitution", "last_performance",
        ]

    def get_substitution(self, slot):
        substitution = (self.context.get("substitutions") or {}).get(slot.pk)
        return SubstitutionSerializer(substitution).data if substitution else None

    def get_last_performance(self, slot):
        # Keyed on the performed exercise: a substituted slot shows the
        # substitute's own history, not the prescription's.
        performed = (self.context.get("performed_exercises") or {}).get(
            slot.pk, slot.exercise
        )
        performances = self.context.get("last_performances") or {}
        session = performances.get(performed.pk)
        return PerformanceSerializer(session).data if session else None


class WorkoutDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutDay
        fields = ["id", "order", "name", "day_of_week"]


class WorkoutDayDetailSerializer(WorkoutDaySerializer):
    """The day screen's whole payload: prescription, where it sits in the
    plan, and the session already logged against it (problem the old shape
    could not express — it returned the prescription and nothing else)."""

    slots = ExerciseSlotSerializer(many=True, read_only=True)
    week_number = serializers.IntegerField(source="week.number", read_only=True)
    phase_number = serializers.IntegerField(source="week.phase.number", read_only=True)
    # The id, not the number: it is what /training/<slug>/phase/<id> routes on,
    # so the day screen can rebuild its own back link.
    phase = serializers.IntegerField(source="week.phase_id", read_only=True)
    program_slug = serializers.CharField(
        source="week.phase.variant.program.slug", read_only=True
    )
    scheduled_on = serializers.SerializerMethodField()
    plan_week = serializers.SerializerMethodField()
    in_active_plan = serializers.SerializerMethodField()
    session = serializers.SerializerMethodField()

    class Meta(WorkoutDaySerializer.Meta):
        fields = WorkoutDaySerializer.Meta.fields + [
            "week_number", "phase_number", "phase", "program_slug",
            "scheduled_on", "plan_week", "in_active_plan", "session", "slots",
        ]

    def get_scheduled_on(self, day):
        return self.context.get("scheduled_on")

    def get_plan_week(self, day):
        return self.context.get("plan_week")

    def get_in_active_plan(self, day):
        return bool(self.context.get("in_active_plan"))

    def get_session(self, day):
        session = self.context.get("session")
        return WorkoutSessionDetailSerializer(session).data if session else None


class WeekSerializer(serializers.ModelSerializer):
    days = WorkoutDaySerializer(many=True, read_only=True)

    class Meta:
        model = Week
        fields = ["id", "number", "is_deload", "is_synthesised", "days"]


class PhaseSerializer(serializers.ModelSerializer):
    weeks = WeekSerializer(many=True, read_only=True)

    class Meta:
        model = Phase
        fields = [
            "id", "number", "label", "weeks_count",
            "weeks_declared_in_source", "number_inferred", "weeks",
        ]


class ProgramVariantSerializer(serializers.ModelSerializer):
    # How long committing to this routine actually is. A COUNT over a handful
    # of rows, and the plan's end date cannot be shown without it.
    total_weeks = serializers.SerializerMethodField()

    class Meta:
        model = ProgramVariant
        fields = ["id", "slug", "days_per_week", "environment", "total_weeks"]

    def get_total_weeks(self, variant) -> int:
        from . import services

        return services.total_weeks(variant)


class ProgramVariantDetailSerializer(ProgramVariantSerializer):
    phases = PhaseSerializer(many=True, read_only=True)

    class Meta(ProgramVariantSerializer.Meta):
        fields = ProgramVariantSerializer.Meta.fields + ["phases"]


class ProgramSerializer(serializers.ModelSerializer):
    variants = ProgramVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Program
        fields = ["id", "slug", "name", "coach", "variants"]


class ProgramDetailSerializer(serializers.ModelSerializer):
    variants = ProgramVariantDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Program
        fields = ["id", "slug", "name", "coach", "variants"]


class ProfileSerializer(serializers.Serializer):
    """The profile only carries preferences now; starting a plan is
    POST /runs/, which needs a date the profile has nowhere to put."""

    weight_unit = serializers.CharField(max_length=3, required=False)


class ProgramRunSerializer(serializers.ModelSerializer):
    variant = ProgramVariantSerializer(read_only=True)
    program = ProgramSerializer(source="variant.program", read_only=True)
    ends_on = serializers.DateField(read_only=True)
    total_weeks = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProgramRun
        fields = [
            "id", "program", "variant", "started_on", "ends_on", "total_weeks",
            "status", "ended_on",
        ]


class ScheduledDaySerializer(serializers.Serializer):
    """One row of a run's calendar: a day of the variant on a real date."""

    day = WorkoutDaySerializer(read_only=True)
    plan_week = serializers.IntegerField(read_only=True)
    scheduled_on = serializers.DateField(read_only=True)
    done = serializers.BooleanField(read_only=True)
    started = serializers.BooleanField(read_only=True)
    session_id = serializers.SerializerMethodField()

    def get_session_id(self, entry):
        session = entry.get("session")
        return session.pk if session else None


class RunStartSerializer(serializers.Serializer):
    variant = serializers.IntegerField()
    # Any date is accepted and snapped back to its ISO Monday: weeks are real
    # weeks, so a plan cannot start on a Wednesday.
    started_on = serializers.DateField(required=False, allow_null=True)


class RunUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[RunStatus.COMPLETED, RunStatus.ABANDONED], required=False
    )
    started_on = serializers.DateField(required=False)


class SubstitutionInputSerializer(serializers.Serializer):
    replacement = serializers.IntegerField()
    scope = serializers.ChoiceField(choices=["session", "program"])
    session = serializers.IntegerField(allow_null=True, required=False)
    reason = serializers.CharField(
        max_length=200, required=False, allow_blank=True, default=""
    )


class SubstitutionSerializer(serializers.ModelSerializer):
    replacement = ExerciseSerializer(read_only=True)

    class Meta:
        model = ExerciseSubstitution
        fields = ["id", "slot", "replacement", "scope", "session", "reason", "created_at"]


class SetLogSerializer(serializers.ModelSerializer):
    performed_exercise = serializers.SlugRelatedField(
        read_only=True, slug_field="name"
    )
    # The client keys its rows by slot + set number; without this it would have
    # to resolve prescription → slot by walking the day tree itself.
    slot = serializers.SerializerMethodField()

    class Meta:
        model = SetLog
        fields = [
            "id", "slot", "prescription", "performed_exercise", "was_substituted",
            "set_number", "weight", "weight_basis", "reps", "rpe", "rir",
            "import_note",
        ]

    def get_slot(self, log):
        return log.prescription.slot_id if log.prescription_id else None


class WorkoutSessionSerializer(serializers.ModelSerializer):
    day = WorkoutDaySerializer(read_only=True)
    # A session with no run was trained outside the active plan (or imported):
    # it counts for exercise history and never for a plan's adherence.
    off_plan = serializers.SerializerMethodField()

    class Meta:
        model = WorkoutSession
        fields = [
            "id", "day", "run", "off_plan", "week_number", "performed_on",
            "completed_at", "notes",
        ]

    def get_off_plan(self, session):
        return session.run_id is None


class WorkoutSessionDetailSerializer(WorkoutSessionSerializer):
    logs = SetLogSerializer(many=True, read_only=True)

    class Meta(WorkoutSessionSerializer.Meta):
        fields = WorkoutSessionSerializer.Meta.fields + ["logs"]


class SessionUpdateSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)
    completed = serializers.BooleanField(required=False)


class SessionInputSerializer(serializers.Serializer):
    """`week_number` is no longer asked for: the day already knows which week
    of which phase it belongs to, and the run knows the date."""

    day = serializers.IntegerField()


class SetLogInputSerializer(serializers.Serializer):
    slot = serializers.IntegerField()
    set_number = serializers.IntegerField(min_value=1)
    weight = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )
    weight_basis = serializers.ChoiceField(
        choices=["total", "per_dumbbell", "bodyweight", "added"], default="total"
    )
    reps = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    rpe = serializers.DecimalField(
        max_digits=3, decimal_places=1, required=False, allow_null=True
    )
    rir = serializers.IntegerField(min_value=0, required=False, allow_null=True)
