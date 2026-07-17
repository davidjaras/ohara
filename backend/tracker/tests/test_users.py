"""Data isolation between users through the API."""

import pytest

from tracker.models import Session

pytestmark = pytest.mark.django_db


class TestDataIsolation:
    def test_users_do_not_see_each_others_sessions(self, client, other_client):
        client.post("/api/sessions/", {"date": "2026-07-06", "minutes": 90}, format="json")
        assert len(client.get("/api/sessions/").json()) == 1
        assert other_client.get("/api/sessions/").json() == []

    def test_stats_are_scoped_to_the_requesting_user(self, client, other_client):
        client.post("/api/sessions/", {"date": "2026-07-06", "minutes": 300}, format="json")
        assert other_client.get("/api/stats/").json()["total_minutes"] == 0

    def test_cannot_delete_another_users_session(self, client, other_client):
        r = client.post("/api/sessions/", {"date": "2026-07-06", "minutes": 90}, format="json")
        pk = r.json()["id"]
        assert other_client.delete(f"/api/sessions/{pk}/").status_code == 404
        assert Session.objects.filter(pk=pk).exists()

    def test_cannot_delete_another_users_measurement(self, client, other_client):
        r = client.post(
            "/api/measurements/",
            {"metric": "peso", "date": "2026-07-06", "value": "78.4", "note": ""},
            format="json",
        )
        pk = r.json()["id"]
        assert other_client.delete(f"/api/measurements/{pk}/").status_code == 404
        assert len(client.get("/api/measurements/?metric=peso").json()) == 1
        assert other_client.get("/api/measurements/?metric=peso").json() == []

    def test_goal_changes_do_not_leak_between_users(self, client, other_client):
        client.put("/api/goal/", {"minutes": 500}, format="json")
        assert client.get("/api/goal/").json()["minutes"] == 500
        assert other_client.get("/api/goal/").json()["minutes"] == 270

    def test_timers_are_independent(self, client, other_client):
        client.post("/api/timer/start/", {}, format="json")
        assert other_client.get("/api/timer/").json() == {"active": False}
        # The other user can run and control their own timer for the same metric.
        r = other_client.post("/api/timer/start/", {}, format="json")
        assert r.status_code == 200
        other_client.post("/api/timer/pause/", {}, format="json")
        assert client.get("/api/timer/").json()["is_paused"] is False
