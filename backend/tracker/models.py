from django.db import models


class Session(models.Model):
    """Una sesión terminada de una métrica tipo "session" (ej. estudio).

    `date` es el día local al que se atribuye la sesión: el día en que empezó
    (para el cronómetro) o el que se eligió en el registro manual. Las
    entradas manuales no tienen started_at/ended_at.
    """

    metric = models.CharField(max_length=50, default="estudio", db_index=True)
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
    """Cronómetro en curso (a lo sumo uno por métrica).

    Se persiste para que un refresh del navegador o un reinicio del servidor
    no pierdan la sesión. `running_since` es null cuando está en pausa;
    `accumulated_seconds` acumula los tramos ya corridos antes de la última
    pausa.
    """

    metric = models.CharField(max_length=50, unique=True)
    started_at = models.DateTimeField()
    accumulated_seconds = models.PositiveIntegerField(default=0)
    running_since = models.DateTimeField(null=True, blank=True)

    @property
    def is_paused(self) -> bool:
        return self.running_since is None

    def elapsed_seconds(self, now) -> int:
        running = 0
        if self.running_since is not None:
            running = max(0, int((now - self.running_since).total_seconds()))
        return self.accumulated_seconds + running

    def __str__(self) -> str:
        state = "pausado" if self.is_paused else "corriendo"
        return f"{self.metric} ({state}) desde {self.started_at}"


class Measurement(models.Model):
    """Una medición puntual de una métrica tipo "measurement" (ej. peso)."""

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
    """Meta semanal en minutos, vigente desde la semana `week_start` (lunes).

    Cambiar la meta crea/actualiza la fila de la semana actual: las semanas
    pasadas se siguen evaluando con la meta que regía entonces.
    """

    metric = models.CharField(max_length=50, db_index=True)
    week_start = models.DateField()
    minutes = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["metric", "week_start"], name="unique_goal_per_week"),
        ]

    def __str__(self) -> str:
        return f"{self.metric} desde {self.week_start}: {self.minutes} min"
