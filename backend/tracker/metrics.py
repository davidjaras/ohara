"""In-code metric registry.

Extensible without data migrations: adding a new metric means adding an entry
here. Existing rows (Session/Measurement/WeeklyGoal) reference the metric by
its text key, so no stored data changes.

Two metric kinds:
- "session": events with a duration (timer or manual entry in minutes), with
  a weekly goal and a streak.
- "measurement": point-in-time values (one value on a date), no duration and
  no goal.
"""

from dataclasses import dataclass

KIND_SESSION = "session"
KIND_MEASUREMENT = "measurement"


@dataclass(frozen=True)
class Metric:
    key: str
    name: str
    kind: str
    unit: str  # display unit ("min", "kg", ...)
    default_weekly_goal_minutes: int | None = None  # only for kind=session


METRICS: dict[str, Metric] = {
    "estudio": Metric(
        key="estudio",
        name="Estudio",
        kind=KIND_SESSION,
        unit="min",
        default_weekly_goal_minutes=270,  # 3 sessions of 90
    ),
}


def get_metric(key: str) -> Metric:
    try:
        return METRICS[key]
    except KeyError:
        raise ValueError(f"Métrica desconocida: {key!r}")


def get_session_metric(key: str) -> Metric:
    metric = get_metric(key)
    if metric.kind != KIND_SESSION:
        raise ValueError(f"La métrica {key!r} no es de tipo sesión")
    return metric


def get_measurement_metric(key: str) -> Metric:
    metric = get_metric(key)
    if metric.kind != KIND_MEASUREMENT:
        raise ValueError(f"La métrica {key!r} no es de tipo medición")
    return metric
