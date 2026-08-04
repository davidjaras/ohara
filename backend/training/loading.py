"""Pure helpers for the JSON loaders.

All reps/tempo parsing lives here so the app never parses prescription
strings at runtime, and so the expansion logic is testable without JSON
files (which are not in the repo).
"""

from .models import Exercise, RestRole


def build_exercise_index() -> dict[str, Exercise]:
    """Map every known spelling (slug, name, name_variants) to its Exercise.

    Programs reference exercises by the name exactly as it appears in their
    own source; the catalogue's name_variants is the resolution key.
    """
    index: dict[str, Exercise] = {}
    for exercise in Exercise.objects.all():
        keys = [exercise.slug, exercise.name, *exercise.name_variants]
        for key in keys:
            if key:
                index[key.strip().lower()] = exercise
    return index


def resolve_exercise(index: dict[str, Exercise], name: str) -> Exercise | None:
    return index.get(name.strip().lower())


def _tempo_code(tempo: dict | None) -> str:
    if not tempo or tempo.get("type") == "unspecified":
        return ""
    if tempo.get("type") == "compound":
        # Two tempos ("2210+2010"): resolved per set for backoff shapes below;
        # for anything else keep the full raw string — do not truncate.
        return tempo.get("raw") or ""
    return tempo.get("code") or tempo.get("raw") or ""


def _reps_fields(reps: dict) -> dict:
    """Per-set fields shared by every set expanded from one reps object."""
    kind = reps.get("type")
    fields = {
        "target_reps_min": None,
        "target_reps_max": None,
        "to_failure": False,
        "hold_seconds": None,
        "cluster_reps": None,
    }
    if kind == "fixed":
        fields["target_reps_min"] = fields["target_reps_max"] = reps.get("value")
    elif kind == "range":
        fields["target_reps_min"] = reps.get("min")
        fields["target_reps_max"] = reps.get("max")
    elif kind == "cluster":
        fields["cluster_reps"] = reps.get("clusters")
    elif kind == "max":
        fields["to_failure"] = True
    elif kind == "time":
        fields["hold_seconds"] = reps.get("seconds")
    # "unspecified"/"unparsed" (0 cases today): keep only reps_raw.
    return fields


def _segment_fields(segment: dict) -> dict:
    if segment.get("type") == "range":
        return {"target_reps_min": segment.get("min"),
                "target_reps_max": segment.get("max")}
    value = segment.get("value")
    return {"target_reps_min": value, "target_reps_max": value}


def expand_prescription(entry: dict) -> list[dict]:
    """Expand one weekly_prescription entry into SetPrescription row dicts.

    Covers the 7 reps shapes plus Glute Coach's per_set arrays (when
    sets_are_uniform is false the real prescription lives there).
    """
    sets_count = entry.get("sets") or 0
    rest_role = entry.get("rest_role") or RestRole.BETWEEN_SETS
    rows: list[dict] = []

    per_set = entry.get("per_set")
    if entry.get("sets_are_uniform") is False and per_set:
        for item in per_set:
            reps = item.get("reps") or {}
            rows.append({
                "set_number": item["set_number"],
                "rest_seconds": item.get("rest_seconds"),
                "rest_role": rest_role,
                "tempo": _tempo_code(item.get("tempo")),
                "reps_per_side": bool(reps.get("unilateral")),
                "reps_raw": reps.get("raw") or "",
                "is_backoff_set": False,
                **_reps_fields(reps),
            })
        return rows

    reps = entry.get("reps") or {}
    tempo = entry.get("tempo") or {}
    common = {
        "rest_seconds": entry.get("rest_seconds"),
        "rest_role": rest_role,
        "reps_per_side": bool(reps.get("unilateral")),
        "reps_raw": reps.get("raw") or "",
    }

    if reps.get("type") == "backoff":
        # N-1 top sets from segment 1 + 1 back-off set from segment 2. A
        # compound tempo pairs with this: first code for the top sets, second
        # for the back-off set.
        segments = reps.get("segments") or []
        top = _segment_fields(segments[0]) if segments else {}
        backoff = _segment_fields(segments[1]) if len(segments) > 1 else top
        tempo_segments = (tempo.get("segments") or []) if tempo.get("type") == "compound" else []
        top_tempo = tempo_segments[0]["code"] if tempo_segments else _tempo_code(tempo)
        backoff_tempo = tempo_segments[1]["code"] if len(tempo_segments) > 1 else top_tempo
        for set_number in range(1, sets_count + 1):
            is_backoff = set_number == sets_count
            rows.append({
                "set_number": set_number,
                "tempo": backoff_tempo if is_backoff else top_tempo,
                "is_backoff_set": is_backoff,
                "to_failure": False,
                "hold_seconds": None,
                "cluster_reps": None,
                **common,
                **(backoff if is_backoff else top),
            })
        return rows

    if reps.get("type") == "per_set":
        values = reps.get("values") or []
        for set_number, value in enumerate(values, start=1):
            rows.append({
                "set_number": set_number,
                "tempo": _tempo_code(tempo),
                "is_backoff_set": False,
                "target_reps_min": value,
                "target_reps_max": value,
                "to_failure": False,
                "hold_seconds": None,
                "cluster_reps": None,
                **common,
            })
        return rows

    fields = _reps_fields(reps)
    for set_number in range(1, sets_count + 1):
        rows.append({
            "set_number": set_number,
            "tempo": _tempo_code(tempo),
            "is_backoff_set": False,
            **common,
            **fields,
        })
    return rows
