from django.db import models
from django.conf import settings


class Session(models.Model):
    """A finished session of a "session"-kind metric (e.g. estudio).

    `date` is the local day the session is attributed to: the day it started
    (timer flow) or the day chosen in a manual entry. Manual entries have no
    started_at/ended_at.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessions"
    )
    metric = models.CharField(
        max_length=50, default=settings.DEFAULT_SESSION_METRIC, db_index=True
    )
    date = models.DateField(db_index=True)
    duration_seconds = models.PositiveIntegerField()
    note = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.metric} {self.date} {self.duration_seconds}s"


class ActiveTimer(models.Model):
    """The in-progress timer (at most one per user and metric).

    Persisted so a browser refresh or server restart never loses the session.
    `running_since` is null while paused; `accumulated_seconds` holds the
    segments already run before the last pause.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="active_timers"
    )
    metric = models.CharField(max_length=50)
    started_at = models.DateTimeField()
    accumulated_seconds = models.PositiveIntegerField(default=0)
    running_since = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "metric"], name="unique_timer_per_user_metric"
            ),
        ]

    @property
    def is_paused(self) -> bool:
        return self.running_since is None

    def elapsed_seconds(self, now) -> int:
        running = 0
        if self.running_since is not None:
            running = max(0, int((now - self.running_since).total_seconds()))
        return self.accumulated_seconds + running

    def __str__(self) -> str:
        state = "paused" if self.is_paused else "running"
        return f"{self.metric} ({state}) since {self.started_at}"


class Measurement(models.Model):
    """A point-in-time value of a "measurement"-kind metric (e.g. peso)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="measurements"
    )
    metric = models.CharField(max_length=50, db_index=True)
    date = models.DateField(db_index=True)
    value = models.DecimalField(max_digits=8, decimal_places=2)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.metric} {self.date} = {self.value}"


class WeeklyGoal(models.Model):
    """Weekly goal in minutes, effective from the ISO week `week_start` (Monday).

    Changing the goal writes the current week's row: past weeks keep being
    evaluated against the goal that was in effect back then.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="weekly_goals"
    )
    metric = models.CharField(max_length=50, db_index=True)
    week_start = models.DateField()
    minutes = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "metric", "week_start"], name="unique_goal_per_user_week"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.metric} from {self.week_start}: {self.minutes} min"


class UserPreference(models.Model):
    """Per-user UI preferences. Currently just the accent color of the theme."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="preference"
    )
    accent_color = models.CharField(
        max_length=20, default=settings.DEFAULT_ACCENT_COLOR
    )

    def __str__(self) -> str:
        return f"{self.user}: {self.accent_color}"
