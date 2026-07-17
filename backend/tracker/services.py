"""Lógica de negocio: cronómetro, agregaciones, metas y racha.

Todas las funciones reciben `now` (datetime aware) o `today` (date local)
explícitos, para que la lógica sea determinista y testeable sin mocks.
Las vistas les pasan timezone.now() / timezone.localdate().
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .metrics import Metric, get_session_metric
from .models import ActiveTimer, Measurement, Session, WeeklyGoal


class TimerError(Exception):
    """Operación inválida sobre el cronómetro (ya existe, no existe, etc.)."""


# --- Semanas -----------------------------------------------------------------

def week_start(day: date) -> date:
    """Lunes de la semana ISO a la que pertenece `day`."""
    return day - timedelta(days=day.weekday())


def local_date(dt: datetime) -> date:
    """Día local (según TIME_ZONE) de un datetime aware."""
    return timezone.localtime(dt).date()


# --- Cronómetro --------------------------------------------------------------

def start_timer(metric_key: str, now: datetime) -> ActiveTimer:
    get_session_metric(metric_key)
    if ActiveTimer.objects.filter(metric=metric_key).exists():
        raise TimerError("Ya hay una sesión en curso para esta métrica.")
    return ActiveTimer.objects.create(
        metric=metric_key, started_at=now, running_since=now
    )


def _get_timer(metric_key: str) -> ActiveTimer:
    try:
        return ActiveTimer.objects.get(metric=metric_key)
    except ActiveTimer.DoesNotExist:
        raise TimerError("No hay ninguna sesión en curso.")


def pause_timer(metric_key: str, now: datetime) -> ActiveTimer:
    timer = _get_timer(metric_key)
    if timer.is_paused:
        raise TimerError("La sesión ya está en pausa.")
    timer.accumulated_seconds = timer.elapsed_seconds(now)
    timer.running_since = None
    timer.save(update_fields=["accumulated_seconds", "running_since"])
    return timer


def resume_timer(metric_key: str, now: datetime) -> ActiveTimer:
    timer = _get_timer(metric_key)
    if not timer.is_paused:
        raise TimerError("La sesión no está en pausa.")
    timer.running_since = now
    timer.save(update_fields=["running_since"])
    return timer


@transaction.atomic
def finish_timer(metric_key: str, now: datetime, note: str = "") -> Session:
    """Cierra el cronómetro y crea la Session. Se atribuye al día de inicio."""
    timer = _get_timer(metric_key)
    session = Session.objects.create(
        metric=metric_key,
        date=local_date(timer.started_at),
        duration_seconds=timer.elapsed_seconds(now),
        note=note,
        started_at=timer.started_at,
        ended_at=now,
    )
    timer.delete()
    return session


def discard_timer(metric_key: str) -> None:
    _get_timer(metric_key).delete()


# --- Registro manual ---------------------------------------------------------

def log_manual_session(metric_key: str, day: date, minutes: int, note: str = "") -> Session:
    get_session_metric(metric_key)
    if minutes <= 0:
        raise ValueError("Los minutos deben ser mayores a cero.")
    return Session.objects.create(
        metric=metric_key, date=day, duration_seconds=minutes * 60, note=note
    )


# --- Metas -------------------------------------------------------------------

def goal_for_week(metric: Metric, week: date) -> int:
    """Meta (minutos) vigente para la semana que empieza en `week`."""
    row = (
        WeeklyGoal.objects.filter(metric=metric.key, week_start__lte=week)
        .order_by("-week_start")
        .first()
    )
    if row is not None:
        return row.minutes
    return metric.default_weekly_goal_minutes or 0


def set_goal(metric_key: str, minutes: int, today: date) -> WeeklyGoal:
    """Fija la meta desde la semana actual en adelante (las pasadas no cambian)."""
    get_session_metric(metric_key)
    if minutes <= 0:
        raise ValueError("La meta debe ser mayor a cero.")
    row, _ = WeeklyGoal.objects.update_or_create(
        metric=metric_key, week_start=week_start(today), defaults={"minutes": minutes}
    )
    # Una meta futura ya registrada quedaría por delante de la nueva; no aplica
    # en el flujo normal (solo escribimos la semana actual), pero por higiene
    # eliminamos filas posteriores a hoy.
    WeeklyGoal.objects.filter(metric=metric_key, week_start__gt=row.week_start).delete()
    return row


# --- Agregaciones ------------------------------------------------------------

def daily_minutes(metric_key: str, start: date, end: date) -> list[dict]:
    """Minutos por día en [start, end], incluyendo días en cero."""
    totals = dict(
        Session.objects.filter(metric=metric_key, date__gte=start, date__lte=end)
        .values_list("date")
        .annotate(total=Sum("duration_seconds"))
        .values_list("date", "total")
    )
    days = []
    day = start
    while day <= end:
        days.append({"date": day, "minutes": (totals.get(day, 0) or 0) // 60})
        day += timedelta(days=1)
    return days


@dataclass
class WeekSummary:
    week_start: date
    minutes: int
    goal_minutes: int
    met: bool


def _week_seconds(metric_key: str) -> dict[date, int]:
    """Total de segundos por semana (solo semanas con datos)."""
    totals: dict[date, int] = {}
    rows = (
        Session.objects.filter(metric=metric_key)
        .values_list("date")
        .annotate(total=Sum("duration_seconds"))
        .values_list("date", "total")
    )
    for day, seconds in rows:
        week = week_start(day)
        totals[week] = totals.get(week, 0) + (seconds or 0)
    return totals


def week_summary(metric: Metric, week: date, week_seconds: dict[date, int]) -> WeekSummary:
    seconds = week_seconds.get(week, 0)
    goal = goal_for_week(metric, week)
    return WeekSummary(
        week_start=week,
        minutes=seconds // 60,
        goal_minutes=goal,
        met=goal > 0 and seconds >= goal * 60,
    )


def weekly_summaries(metric_key: str, today: date, weeks: int) -> list[WeekSummary]:
    """Resumen de las últimas `weeks` semanas, la actual incluida, ascendente."""
    metric = get_session_metric(metric_key)
    totals = _week_seconds(metric_key)
    current = week_start(today)
    return [
        week_summary(metric, current - timedelta(weeks=i), totals)
        for i in range(weeks - 1, -1, -1)
    ]


def current_streak(metric_key: str, today: date) -> int:
    """Semanas cumplidas consecutivas.

    La semana en curso suma solo si ya cumplió la meta; mientras no termine,
    no rompe la racha. Hacia atrás, la racha corta en la primera semana
    incumplida.
    """
    metric = get_session_metric(metric_key)
    totals = _week_seconds(metric_key)
    current = week_start(today)

    streak = 0
    if week_summary(metric, current, totals).met:
        streak += 1
    week = current - timedelta(weeks=1)
    # Las semanas anteriores al primer dato nunca cumplen, así que el corte
    # llega naturalmente; no hace falta un límite extra.
    while week_summary(metric, week, totals).met:
        streak += 1
        week -= timedelta(weeks=1)
    return streak


def total_minutes(metric_key: str) -> int:
    seconds = (
        Session.objects.filter(metric=metric_key).aggregate(total=Sum("duration_seconds"))["total"]
        or 0
    )
    return seconds // 60


# --- Mediciones --------------------------------------------------------------

def log_measurement(metric_key: str, day: date, value, note: str = "") -> Measurement:
    from .metrics import get_measurement_metric

    get_measurement_metric(metric_key)
    return Measurement.objects.create(metric=metric_key, date=day, value=value, note=note)
