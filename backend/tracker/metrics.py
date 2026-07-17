"""Registro de métricas en código.

Extensible sin migrar datos: agregar una métrica nueva es agregar una entrada
acá. Las filas existentes (Session/Measurement/WeeklyGoal) referencian la
métrica por su clave de texto, así que ningún dato cambia.

Dos clases de métrica:
- "session": eventos con duración (cronómetro o registro manual en minutos),
  con meta semanal y racha.
- "measurement": mediciones puntuales (un valor en una fecha), sin duración
  ni meta.
"""

from dataclasses import dataclass

KIND_SESSION = "session"
KIND_MEASUREMENT = "measurement"


@dataclass(frozen=True)
class Metric:
    key: str
    name: str
    kind: str
    unit: str  # unidad para mostrar ("min", "kg", ...)
    default_weekly_goal_minutes: int | None = None  # solo para kind=session


METRICS: dict[str, Metric] = {
    "estudio": Metric(
        key="estudio",
        name="Estudio",
        kind=KIND_SESSION,
        unit="min",
        default_weekly_goal_minutes=270,  # 3 sesiones de 90
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
