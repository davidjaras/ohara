"""Metric access helpers.

The metric registry lives in Django settings. Existing rows
(Session/Measurement/WeeklyGoal) reference the metric by its text key, so
configuration changes do not require data migrations.

Two metric kinds:
- "session": events with a duration (timer or manual entry in minutes), with
  a weekly goal and a streak.
- "measurement": point-in-time values (one value on a date), no duration and
  no goal.
"""

from dataclasses import dataclass

from django.conf import settings
from django.utils.translation import gettext as _


@dataclass(frozen=True)
class Metric:
    key: str
    name: str
    kind: str
    unit: str  # display unit ("min", "kg", ...)
    default_weekly_goal_minutes: int | None = None  # only for kind=session


def list_metrics() -> list[Metric]:
    return [Metric(**data) for data in settings.METRICS.values()]


def get_metric(key: str) -> Metric:
    try:
        data = settings.METRICS[key]
    except KeyError:
        raise ValueError(_("Unknown metric: %s") % key)
    return Metric(**data)


def get_session_metric(key: str) -> Metric:
    metric = get_metric(key)
    if metric.kind != settings.KIND_SESSION:
        raise ValueError(_("Metric %s is not a session metric") % key)
    return metric


def get_measurement_metric(key: str) -> Metric:
    metric = get_metric(key)
    if metric.kind != settings.KIND_MEASUREMENT:
        raise ValueError(_("Metric %s is not a measurement metric") % key)
    return metric
