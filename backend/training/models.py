from django.conf import settings
from django.db import models


class Muscle(models.TextChoices):
    CHEST = "chest", "Chest"
    LATS = "lats", "Lats"
    UPPER_BACK = "upper_back", "Upper back"
    TRAPS = "traps", "Traps"
    FRONT_DELTS = "front_delts", "Front delts"
    LATERAL_DELTS = "lateral_delts", "Lateral delts"
    REAR_DELTS = "rear_delts", "Rear delts"
    BICEPS = "biceps", "Biceps"
    TRICEPS = "triceps", "Triceps"
    FOREARMS = "forearms", "Forearms"
    QUADS = "quads", "Quads"
    HAMSTRINGS = "hamstrings", "Hamstrings"
    GLUTES = "glutes", "Glutes"
    ABDUCTORS = "abductors", "Abductors"
    ADDUCTORS = "adductors", "Adductors"
    CALVES = "calves", "Calves"
    LOWER_BACK = "lower_back", "Lower back"
    ABS = "abs", "Abs"


class MovementPattern(models.TextChoices):
    HORIZONTAL_PUSH = "horizontal_push", "Horizontal push"
    VERTICAL_PUSH = "vertical_push", "Vertical push"
    HORIZONTAL_PULL = "horizontal_pull", "Horizontal pull"
    VERTICAL_PULL = "vertical_pull", "Vertical pull"
    SQUAT = "squat", "Squat"
    HINGE = "hinge", "Hinge"
    LUNGE = "lunge", "Lunge"
    ISOLATION = "isolation", "Isolation"


class Setting(models.TextChoices):
    HOME = "home", "At home"
    GYM = "gym", "At the gym"


class RestRole(models.TextChoices):
    BETWEEN_SETS = "between_sets", "Between sets"
    SUPERSET_TRANSITION = "superset_transition", "Superset transition"
    SUPERSET_ROUND_END = "superset_round_end", "Superset round end"


class SubstitutionScope(models.TextChoices):
    SESSION = "session", "This session only"
    PROGRAM = "program", "Whole program"


class RunStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    ABANDONED = "abandoned", "Abandoned"


class WeightBasis(models.TextChoices):
    TOTAL = "total", "Total weight"
    PER_DUMBBELL = "per_dumbbell", "Per dumbbell"
    BODYWEIGHT = "bodyweight", "Bodyweight"
    ADDED = "added", "Weight added to bodyweight"


class Equipment(models.Model):
    """Global catalogue of implements. A table rather than an enum so it can
    grow without a migration."""

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ["slug"]

    def __str__(self) -> str:
        return self.name


class Exercise(models.Model):
    # Catalogue slugs run up to 72 characters; SlugField's default 50 truncates.
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    # Source spellings; the program loader resolves exercise names through them.
    name_variants = models.JSONField(default=list, blank=True)

    primary_muscle = models.CharField(
        max_length=20, choices=Muscle.choices, db_index=True
    )
    secondary_muscles = models.JSONField(default=list, blank=True)
    movement_pattern = models.CharField(
        max_length=20, choices=MovementPattern.choices, blank=True
    )

    equipment_required = models.ManyToManyField(
        Equipment, related_name="exercises", blank=True
    )
    is_unilateral = models.BooleanField(default=False)

    # 'gym' when it needs a commercial-gym machine (cable, leg press, Smith...);
    # 'home' otherwise. 'home' means "needs no machine", not "doable today":
    # the picker must still show equipment_required on every option.
    setting = models.CharField(max_length=4, choices=Setting.choices, db_index=True)

    # Only in the catalogue because a historical log substituted it in.
    introduced_by_user_substitution = models.BooleanField(default=False)

    # Reserved for the ExerciseDB session (out of scope now); stay empty.
    exercisedb_id = models.CharField(max_length=40, blank=True, db_index=True)
    preview_gif = models.FileField(upload_to="exercise_gifs/", blank=True)

    needs_review = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Program(models.Model):
    # No is_active here: which program is active is per user and lives in the
    # user's active ProgramRun.
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    coach = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ProgramVariant(models.Model):
    program = models.ForeignKey(
        Program, related_name="variants", on_delete=models.CASCADE
    )
    slug = models.SlugField()  # "4-days-home", "default"
    days_per_week = models.PositiveSmallIntegerField(null=True, blank=True)
    environment = models.CharField(max_length=10, blank=True)  # "gym" | "home"

    class Meta:
        ordering = ["slug"]
        constraints = [
            models.UniqueConstraint(fields=["program", "slug"], name="uniq_variant"),
        ]

    def __str__(self) -> str:
        return f"{self.program.slug}/{self.slug}"


class Phase(models.Model):
    variant = models.ForeignKey(
        ProgramVariant, related_name="phases", on_delete=models.CASCADE
    )
    number = models.PositiveSmallIntegerField()
    label = models.CharField(max_length=120)
    weeks_count = models.PositiveSmallIntegerField()
    # False when the source day tables carry no week column (Glute Coach); its
    # weeks are then synthesised copies of the phase-level prescription.
    weeks_declared_in_source = models.BooleanField(default=True)
    # Glute Coach's fourth folder is named "Phase" with no number; the order
    # was assigned by elimination and needs David's confirmation.
    number_inferred = models.BooleanField(default=False)
    review_note = models.TextField(blank=True)

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(fields=["variant", "number"], name="uniq_phase"),
        ]

    def __str__(self) -> str:
        return f"{self.variant} phase {self.number}"


class Week(models.Model):
    phase = models.ForeignKey(Phase, related_name="weeks", on_delete=models.CASCADE)
    number = models.PositiveSmallIntegerField()
    # No program marks deloads (MM2 p.14 relies on autoregulation); the field
    # exists for manual use, not for the import.
    is_deload = models.BooleanField(default=False)
    is_synthesised = models.BooleanField(default=False)

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(fields=["phase", "number"], name="uniq_week"),
        ]
        indexes = [models.Index(fields=["phase", "number"])]

    def __str__(self) -> str:
        return f"{self.phase} week {self.number}"


class WorkoutDay(models.Model):
    week = models.ForeignKey(Week, related_name="days", on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=100)  # "Lower 1", "Chest & Back 1"
    day_of_week = models.CharField(max_length=12, blank=True)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["week", "order"], name="uniq_day"),
        ]

    def __str__(self) -> str:
        return f"{self.week} · {self.name}"


class ExerciseSlot(models.Model):
    """An exercise at position N of a day. NOT the exercise itself."""

    day = models.ForeignKey(WorkoutDay, related_name="slots", on_delete=models.CASCADE)
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT)
    order = models.PositiveSmallIntegerField()

    series_label = models.CharField(max_length=2, blank=True)  # "A", "B"
    series_position = models.PositiveSmallIntegerField(null=True, blank=True)
    coach_annotation = models.TextField(blank=True)
    modifiers = models.JSONField(default=list, blank=True)  # parsed techniques

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["day", "order"], name="uniq_slot"),
        ]

    @property
    def is_superset(self) -> bool:
        return self.series_position is not None

    def __str__(self) -> str:
        return f"{self.day} #{self.order} {self.exercise.name}"


class SetPrescription(models.Model):
    slot = models.ForeignKey(
        ExerciseSlot, related_name="sets", on_delete=models.CASCADE
    )
    set_number = models.PositiveSmallIntegerField()

    target_reps_min = models.PositiveSmallIntegerField(null=True, blank=True)
    target_reps_max = models.PositiveSmallIntegerField(null=True, blank=True)
    to_failure = models.BooleanField(default=False)  # 'MAX REPS'
    hold_seconds = models.PositiveSmallIntegerField(null=True, blank=True)
    reps_per_side = models.BooleanField(default=False)  # 'Each Leg'

    rest_seconds = models.PositiveSmallIntegerField(null=True, blank=True)
    # Inside supersets the Rest column changes meaning by position: 15 s is the
    # A1→A2 transition, 150 s closes the round. The timer must respect this.
    rest_role = models.CharField(max_length=24, choices=RestRole.choices)
    tempo = models.CharField(max_length=9, blank=True)  # "3010", "2210+2010"

    is_backoff_set = models.BooleanField(default=False)
    cluster_reps = models.JSONField(null=True, blank=True)  # [8,5,3] rest-pause

    reps_raw = models.CharField(max_length=60, blank=True)  # original string

    class Meta:
        ordering = ["set_number"]
        constraints = [
            models.UniqueConstraint(fields=["slot", "set_number"], name="uniq_set"),
        ]

    def __str__(self) -> str:
        return f"{self.slot} set {self.set_number}"


class TrainingProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="training_profile",
        on_delete=models.CASCADE,
    )
    enabled = models.BooleanField(default=False)
    weight_unit = models.CharField(max_length=3, default="kg")

    # What the user is doing is NOT here: it is the active ProgramRun, which
    # also knows when it started and when it ends. A duplicate pointer on the
    # profile would be a second source of truth for the same question.

    def __str__(self) -> str:
        return f"{self.user} (enabled={self.enabled})"


class ProgramAccess(models.Model):
    """Explicit grant. Without a row here, the program does not exist for
    that user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="program_access",
        on_delete=models.CASCADE,
    )
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "program"], name="uniq_program_access"
            ),
        ]
        indexes = [models.Index(fields=["user", "program"])]

    def __str__(self) -> str:
        return f"{self.user} → {self.program}"


class ProgramRun(models.Model):
    """A commitment to run one variant from a start date to an end date.

    Activating a program is not a label, it is a plan: the run anchors every
    WorkoutDay of the variant to a real date, so "which day am I on" stops
    being a question the UI has to ask the user.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="program_runs",
        on_delete=models.CASCADE,
    )
    variant = models.ForeignKey(ProgramVariant, on_delete=models.PROTECT)
    # Always an ISO Monday: every program names its days MONDAY..SATURDAY and
    # the rest of Ohara counts Monday-start weeks. services.start_run snaps it.
    started_on = models.DateField()
    status = models.CharField(
        max_length=10, choices=RunStatus.choices, default=RunStatus.ACTIVE
    )
    # Stamped when the run stops, whether it was finished or dropped. The
    # scheduled end date is derived from started_on and the variant's length.
    ended_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_on", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status=RunStatus.ACTIVE),
                name="uniq_active_run",
            ),
        ]
        indexes = [models.Index(fields=["user", "-started_on"])]

    def __str__(self) -> str:
        return f"{self.user} → {self.variant} from {self.started_on}"


class WorkoutSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="workout_sessions",
        on_delete=models.CASCADE,
        db_index=True,
    )
    # Null means off-plan: a day trained outside the active run, or a row from
    # the historical import. Those keep counting for exercise history and never
    # count for a plan's adherence.
    run = models.ForeignKey(
        ProgramRun,
        related_name="sessions",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    day = models.ForeignKey(WorkoutDay, on_delete=models.PROTECT)
    week_number = models.PositiveSmallIntegerField()  # the REAL week being run
    # Null for imported historical rows: the source carries no dates and
    # inventing plausible ones unmarked was ruled out.
    performed_on = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    # Batch tag for historical imports; the importer deletes the batch before
    # re-importing, which is what makes it idempotent.
    imported_from = models.CharField(max_length=40, blank=True, db_index=True)

    class Meta:
        # Newest first, with the undated historical import last rather than
        # first: Postgres sorts NULLs before everything in DESC, which would
        # rank a 2023 imported row above yesterday's workout.
        ordering = [models.F("performed_on").desc(nulls_last=True), "-id"]
        indexes = [models.Index(fields=["user", "-performed_on"])]
        constraints = [
            # A day appears once in a plan, so it gets one session in that run.
            # Postgres treats NULLs as distinct, which leaves off-plan sessions
            # (run=None) unconstrained — exactly what we want.
            models.UniqueConstraint(fields=["run", "day"], name="uniq_run_day"),
        ]

    def __str__(self) -> str:
        return f"{self.user} {self.day.name} week {self.week_number}"


class SetLog(models.Model):
    session = models.ForeignKey(
        WorkoutSession, related_name="logs", on_delete=models.CASCADE
    )
    prescription = models.ForeignKey(
        SetPrescription, null=True, blank=True, on_delete=models.SET_NULL
    )

    # CRITICAL: what was actually performed, which may not be what was
    # prescribed. 13 historical entries substitute the exercise and the weight
    # belongs to the substitute, not the prescription.
    performed_exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT)
    was_substituted = models.BooleanField(default=False)

    set_number = models.PositiveSmallIntegerField()
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    weight_basis = models.CharField(
        max_length=14, choices=WeightBasis.choices, default=WeightBasis.TOTAL
    )
    reps = models.PositiveSmallIntegerField(null=True, blank=True)

    rpe = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    rir = models.PositiveSmallIntegerField(null=True, blank=True)

    imported_from = models.CharField(max_length=40, blank=True)
    import_note = models.TextField(blank=True)

    class Meta:
        ordering = ["set_number"]
        indexes = [models.Index(fields=["performed_exercise", "-id"])]

    def __str__(self) -> str:
        return f"{self.performed_exercise.name} set {self.set_number}"


class ExerciseSubstitution(models.Model):
    # The slot is global (part of the program); the substitution is the USER'S.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="substitutions",
        on_delete=models.CASCADE,
    )
    slot = models.ForeignKey(
        ExerciseSlot, related_name="substitutions", on_delete=models.CASCADE
    )
    replacement = models.ForeignKey(Exercise, on_delete=models.PROTECT)
    scope = models.CharField(max_length=10, choices=SubstitutionScope.choices)
    session = models.ForeignKey(
        WorkoutSession, null=True, blank=True, on_delete=models.CASCADE
    )
    reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.user}: {self.slot} → {self.replacement.name}"
