from rest_framework import serializers

from .models import (
    Exercise,
    ExerciseSlot,
    ExerciseSubstitution,
    Phase,
    Program,
    ProgramVariant,
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


class ExerciseSlotSerializer(serializers.ModelSerializer):
    exercise = ExerciseSerializer(read_only=True)
    sets = SetPrescriptionSerializer(many=True, read_only=True)

    class Meta:
        model = ExerciseSlot
        fields = [
            "id", "order", "series_label", "series_position", "is_superset",
            "coach_annotation", "modifiers", "exercise", "sets",
        ]


class WorkoutDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutDay
        fields = ["id", "order", "name", "day_of_week"]


class WorkoutDayDetailSerializer(WorkoutDaySerializer):
    slots = ExerciseSlotSerializer(many=True, read_only=True)

    class Meta(WorkoutDaySerializer.Meta):
        fields = WorkoutDaySerializer.Meta.fields + ["slots"]


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
    class Meta:
        model = ProgramVariant
        fields = ["id", "slug", "days_per_week", "environment"]


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
    active_variant = serializers.IntegerField(allow_null=True, required=False)
    weight_unit = serializers.CharField(max_length=3, required=False)


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

    class Meta:
        model = SetLog
        fields = [
            "id", "prescription", "performed_exercise", "was_substituted",
            "set_number", "weight", "weight_basis", "reps", "rpe", "rir",
            "import_note",
        ]


class WorkoutSessionSerializer(serializers.ModelSerializer):
    day = WorkoutDaySerializer(read_only=True)

    class Meta:
        model = WorkoutSession
        fields = [
            "id", "day", "week_number", "performed_on", "completed_at", "notes",
        ]


class WorkoutSessionDetailSerializer(WorkoutSessionSerializer):
    logs = SetLogSerializer(many=True, read_only=True)

    class Meta(WorkoutSessionSerializer.Meta):
        fields = WorkoutSessionSerializer.Meta.fields + ["logs"]


class SessionInputSerializer(serializers.Serializer):
    day = serializers.IntegerField()
    week_number = serializers.IntegerField(min_value=1)
    performed_on = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


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
