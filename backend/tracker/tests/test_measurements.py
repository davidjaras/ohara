"""Tests for measurement-kind metrics (peso), added as the extensibility check."""

from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal

import pytest

from tracker import services
from tracker.models import Measurement

pytestmark = pytest.mark.django_db


class TestMeasurementServices:
    def test_log_measurement(self, user):
        row = services.log_measurement(
            user, "peso", date(2026, 7, 6), Decimal("78.40"), "post vacaciones"
        )
        assert row.value == Decimal("78.40")
        assert row.note == "post vacaciones"
        assert row.user == user

    def test_rejects_session_metric(self, user):
        with pytest.raises(ValueError):
            services.log_measurement(user, "estudio", date(2026, 7, 6), Decimal("78.40"))

    def test_rejects_unknown_metric(self, user):
        with pytest.raises(ValueError):
            services.log_measurement(user, "altura", date(2026, 7, 6), Decimal("1.80"))

    def test_session_kind_guards_reject_measurement_metric(self, user):
        now = datetime(2026, 7, 6, 10, 0, tzinfo=dt_timezone.utc)
        with pytest.raises(ValueError):
            services.start_timer(user, "peso", now)
        with pytest.raises(ValueError):
            services.log_manual_session(user, "peso", date(2026, 7, 6), 30)
        with pytest.raises(ValueError):
            services.set_goal(user, "peso", 100, date(2026, 7, 6))


class TestMeasurementApi:
    def test_create_list_delete(self, client):
        r = client.post(
            "/api/measurements/",
            {"metric": "peso", "date": "2026-07-06", "value": "78.4", "note": ""},
            format="json",
        )
        assert r.status_code == 201
        assert r.json()["value"] == "78.40"

        rows = client.get("/api/measurements/?metric=peso").json()
        assert len(rows) == 1

        assert client.delete(f"/api/measurements/{rows[0]['id']}/").status_code == 204
        assert Measurement.objects.count() == 0

    def test_list_requires_metric(self, client):
        assert client.get("/api/measurements/").status_code == 400

    def test_create_rejects_session_metric(self, client):
        r = client.post(
            "/api/measurements/",
            {"metric": "estudio", "date": "2026-07-06", "value": "78.4", "note": ""},
            format="json",
        )
        assert r.status_code == 400

    def test_metrics_endpoint_lists_peso(self, client):
        metrics = {m["key"]: m for m in client.get("/api/metrics/").json()}
        assert metrics["peso"]["kind"] == "measurement"
        assert metrics["peso"]["unit"] == "kg"

    def test_estudio_data_untouched_by_new_metric(self, client):
        # The whole estudio flow keeps working with peso registered: no
        # migration, no behavior change.
        client.post("/api/sessions/", {"date": "2026-07-06", "minutes": 90}, format="json")
        stats = client.get("/api/stats/").json()
        assert stats["total_minutes"] == 90
