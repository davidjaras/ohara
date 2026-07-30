"""Tests for the logging flow through the REST API."""

from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from tracker.models import Session

pytestmark = pytest.mark.django_db


class TestAuthRequired:
    @pytest.mark.parametrize(
        "method,path",
        [
            ("get", "/api/stats/"),
            ("get", "/api/sessions/"),
            ("get", "/api/timer/"),
            ("get", "/api/me/"),
            ("post", "/api/timer/start/"),
            ("put", "/api/goal/"),
        ],
    )
    def test_anonymous_requests_are_rejected(self, method, path):
        anonymous = APIClient()
        response = getattr(anonymous, method)(path, {}, format="json")
        assert response.status_code in (401, 403)

    def test_me_returns_current_username(self, client, user):
        assert client.get("/api/me/").json() == {"username": user.username}


class TestTimerFlow:
    def test_start_pause_resume_finish(self, client):
        t0 = timezone.now()

        with mock.patch("tracker.views.timezone.now", return_value=t0):
            r = client.post("/api/timer/start/", {"metric": "estudio"}, format="json")
        assert r.status_code == 200
        assert r.json()["active"] is True
        assert r.json()["is_paused"] is False

        with mock.patch("tracker.views.timezone.now", return_value=t0 + timedelta(minutes=10)):
            r = client.post("/api/timer/pause/", {}, format="json")
        assert r.status_code == 200
        assert r.json()["is_paused"] is True
        assert r.json()["elapsed_seconds"] == 600

        with mock.patch("tracker.views.timezone.now", return_value=t0 + timedelta(minutes=20)):
            r = client.post("/api/timer/resume/", {}, format="json")
        assert r.status_code == 200
        assert r.json()["is_paused"] is False

        with mock.patch("tracker.views.timezone.now", return_value=t0 + timedelta(minutes=25)):
            r = client.post(
                "/api/timer/finish/", {"note": "aprendí DRF"}, format="json"
            )
        assert r.status_code == 201
        body = r.json()
        assert body["duration_seconds"] == 15 * 60  # 10 running + 5 after resume
        assert body["note"] == "aprendí DRF"

        session = Session.objects.get()
        assert session.duration_seconds == 15 * 60
        assert client.get("/api/timer/").json() == {"active": False}

    def test_timer_state_survives_reload(self, client):
        client.post("/api/timer/start/", {}, format="json")
        r = client.get("/api/timer/")
        assert r.json()["active"] is True

    def test_double_start_conflicts(self, client):
        client.post("/api/timer/start/", {}, format="json")
        r = client.post("/api/timer/start/", {}, format="json")
        assert r.status_code == 409

    def test_finish_without_timer_conflicts(self, client):
        r = client.post("/api/timer/finish/", {"note": ""}, format="json")
        assert r.status_code == 409

    def test_discard(self, client):
        client.post("/api/timer/start/", {}, format="json")
        assert client.delete("/api/timer/").status_code == 204
        assert Session.objects.count() == 0


class TestManualEntry:
    def test_create_and_list(self, client):
        r = client.post(
            "/api/sessions/",
            {"date": "2026-07-06", "minutes": 90, "note": "álgebra"},
            format="json",
        )
        assert r.status_code == 201
        assert r.json()["minutes"] == 90

        rows = client.get("/api/sessions/").json()
        assert len(rows) == 1
        assert rows[0]["note"] == "álgebra"

    def test_rejects_invalid_minutes(self, client):
        r = client.post("/api/sessions/", {"date": "2026-07-06", "minutes": 0}, format="json")
        assert r.status_code == 400

    def test_rejects_more_minutes_than_a_day_has(self, client):
        r = client.post("/api/sessions/", {"date": "2026-07-06", "minutes": 1441}, format="json")
        assert r.status_code == 400

    def test_rejects_entry_that_overflows_the_day(self, client):
        client.post("/api/sessions/", {"date": "2026-07-06", "minutes": 1400}, format="json")
        r = client.post("/api/sessions/", {"date": "2026-07-06", "minutes": 41}, format="json")
        assert r.status_code == 400
        assert Session.objects.count() == 1

    def test_rejects_future_date(self, client):
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()
        r = client.post("/api/sessions/", {"date": tomorrow, "minutes": 30}, format="json")
        assert r.status_code == 400

    def test_delete(self, client):
        r = client.post("/api/sessions/", {"date": "2026-07-06", "minutes": 30}, format="json")
        pk = r.json()["id"]
        assert client.delete(f"/api/sessions/{pk}/").status_code == 204
        assert Session.objects.count() == 0


class TestEditEntry:
    def _create(self, client, minutes=30, day="2026-07-06"):
        return client.post(
            "/api/sessions/", {"date": day, "minutes": minutes}, format="json"
        ).json()["id"]

    def test_patch_updates_minutes_and_note(self, client):
        pk = self._create(client)
        r = client.patch(f"/api/sessions/{pk}/", {"minutes": 75, "note": "cálculo"}, format="json")
        assert r.status_code == 200
        assert r.json()["minutes"] == 75
        assert r.json()["note"] == "cálculo"

    def test_patch_rejects_empty_body(self, client):
        pk = self._create(client)
        assert client.patch(f"/api/sessions/{pk}/", {}, format="json").status_code == 400

    def test_patch_rejects_overflowing_the_day(self, client):
        self._create(client, minutes=1000)
        pk = self._create(client, minutes=400)
        r = client.patch(f"/api/sessions/{pk}/", {"minutes": 441}, format="json")
        assert r.status_code == 400

    def test_patch_of_another_users_session_is_404(self, client, other_client):
        pk = self._create(client)
        r = other_client.patch(f"/api/sessions/{pk}/", {"minutes": 10}, format="json")
        assert r.status_code == 404


class TestGoal:
    def test_get_default_and_update(self, client):
        assert client.get("/api/goal/").json() == {"metric": "estudio", "minutes": 270}
        r = client.put("/api/goal/", {"minutes": 300}, format="json")
        assert r.status_code == 200
        assert client.get("/api/goal/").json()["minutes"] == 300

    def test_rejects_goal_beyond_the_minutes_a_week_has(self, client):
        assert client.put("/api/goal/", {"minutes": 99999}, format="json").status_code == 400


class TestStats:
    def test_dashboard_payload(self, client):
        today = timezone.localdate()
        client.post(
            "/api/sessions/", {"date": str(today), "minutes": 300, "note": ""}, format="json"
        )
        r = client.get("/api/stats/?weeks=4")
        assert r.status_code == 200
        body = r.json()
        assert body["week_minutes"] == 300
        assert body["week_met"] is True
        assert body["streak_weeks"] == 1
        assert body["total_minutes"] == 300
        assert len(body["weekly"]) == 4
        assert body["weekly"][-1]["met"] is True
        # Cumulative series covers Monday through today only.
        assert len(body["week_cumulative"]) == today.isoweekday()
        assert body["week_cumulative"][-1]["cumulative_minutes"] == 300

    def test_unknown_metric_is_400(self, client):
        assert client.get("/api/stats/?metric=nope").status_code == 400


class TestMetrics:
    def test_lists_registered_metrics(self, client):
        keys = [m["key"] for m in client.get("/api/metrics/").json()]
        assert "estudio" in keys
