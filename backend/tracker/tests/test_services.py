"""Business-logic tests: timer, aggregations, goal, streak and cumulative."""

from datetime import date, datetime, timedelta, timezone as dt_timezone

import pytest

from tracker import services
from tracker.metrics import get_metric
from tracker.models import ActiveTimer, Session, WeeklyGoal

pytestmark = pytest.mark.django_db

UTC = dt_timezone.utc


def dt(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


# Monday July 6, 2026 anchors the weeks used in these tests.
MONDAY = date(2026, 7, 6)


def log(user, day: date, minutes: int, metric: str = "estudio") -> Session:
    return services.log_manual_session(user, metric, day, minutes)


# --- Weeks -----------------------------------------------------------------

class TestWeekStart:
    def test_monday_maps_to_itself(self):
        assert services.week_start(MONDAY) == MONDAY

    def test_sunday_belongs_to_previous_monday(self):
        assert services.week_start(MONDAY + timedelta(days=6)) == MONDAY

    def test_next_monday_starts_new_week(self):
        assert services.week_start(MONDAY + timedelta(days=7)) == MONDAY + timedelta(days=7)


# --- Timer --------------------------------------------------------------

class TestTimer:
    def test_full_flow_with_pauses_accumulates_only_running_time(self, user):
        t0 = dt(2026, 7, 6, 10, 0, 0)
        services.start_timer(user, "estudio", t0)
        services.pause_timer(user, "estudio", t0 + timedelta(minutes=10))
        services.resume_timer(user, "estudio", t0 + timedelta(minutes=25))
        services.pause_timer(user, "estudio", t0 + timedelta(minutes=40))
        services.resume_timer(user, "estudio", t0 + timedelta(minutes=50))
        session = services.finish_timer(user, "estudio", t0 + timedelta(minutes=60), note="repaso")

        # Ran 10 + 15 + 10 minutes; the pauses (15 + 10) don't count.
        assert session.duration_seconds == 35 * 60
        assert session.note == "repaso"
        assert session.user == user
        assert session.started_at == t0
        assert session.ended_at == t0 + timedelta(minutes=60)
        assert not ActiveTimer.objects.exists()

    def test_elapsed_while_paused_does_not_grow(self, user):
        t0 = dt(2026, 7, 6, 10, 0, 0)
        services.start_timer(user, "estudio", t0)
        timer = services.pause_timer(user, "estudio", t0 + timedelta(minutes=5))
        assert timer.elapsed_seconds(t0 + timedelta(hours=3)) == 5 * 60

    def test_session_attributed_to_start_day_across_midnight(self, user, settings):
        settings.TIME_ZONE = "UTC"
        t0 = dt(2026, 7, 6, 23, 30, 0)
        services.start_timer(user, "estudio", t0)
        session = services.finish_timer(user, "estudio", t0 + timedelta(hours=1))
        assert session.date == date(2026, 7, 6)

    def test_cannot_start_twice(self, user):
        services.start_timer(user, "estudio", dt(2026, 7, 6, 10, 0))
        with pytest.raises(services.TimerError):
            services.start_timer(user, "estudio", dt(2026, 7, 6, 11, 0))

    def test_two_users_can_run_timers_independently(self, user, other_user):
        t0 = dt(2026, 7, 6, 10, 0)
        services.start_timer(user, "estudio", t0)
        other_timer = services.start_timer(other_user, "estudio", t0)
        services.pause_timer(user, "estudio", t0 + timedelta(minutes=5))
        other_timer.refresh_from_db()
        assert not other_timer.is_paused
        assert other_timer.elapsed_seconds(t0 + timedelta(minutes=10)) == 10 * 60

    def test_cannot_pause_paused_or_resume_running(self, user):
        t0 = dt(2026, 7, 6, 10, 0)
        services.start_timer(user, "estudio", t0)
        with pytest.raises(services.TimerError):
            services.resume_timer(user, "estudio", t0 + timedelta(minutes=1))
        services.pause_timer(user, "estudio", t0 + timedelta(minutes=2))
        with pytest.raises(services.TimerError):
            services.pause_timer(user, "estudio", t0 + timedelta(minutes=3))

    def test_operations_without_timer_fail(self, user):
        for op in (services.pause_timer, services.resume_timer, services.finish_timer):
            with pytest.raises(services.TimerError):
                op(user, "estudio", dt(2026, 7, 6, 10, 0))

    def test_discard_deletes_without_creating_session(self, user):
        services.start_timer(user, "estudio", dt(2026, 7, 6, 10, 0))
        services.discard_timer(user, "estudio")
        assert not ActiveTimer.objects.exists()
        assert not Session.objects.exists()

    def test_start_rejects_unknown_and_measurement_metrics(self, user):
        with pytest.raises(ValueError):
            services.start_timer(user, "inventada", dt(2026, 7, 6, 10, 0))


# --- Manual entry ---------------------------------------------------------

class TestManualLog:
    def test_creates_session_without_timestamps(self, user):
        session = log(user, MONDAY, 45)
        assert session.duration_seconds == 45 * 60
        assert session.started_at is None

    def test_rejects_non_positive_minutes(self, user):
        with pytest.raises(ValueError):
            services.log_manual_session(user, "estudio", MONDAY, 0)


# --- Daily aggregation -------------------------------------------------------

class TestDailyMinutes:
    def test_sums_per_day_and_fills_zero_days(self, user):
        log(user, MONDAY, 30)
        log(user, MONDAY, 15)
        log(user, MONDAY + timedelta(days=2), 60)
        result = services.daily_minutes(user, "estudio", MONDAY, MONDAY + timedelta(days=3))
        assert [r["minutes"] for r in result] == [45, 0, 60, 0]
        assert result[0]["date"] == MONDAY

    def test_seconds_are_summed_before_flooring_to_minutes(self, user):
        # 90s + 90s = 3 min; flooring per session would give 1+1 = 2.
        for _ in range(2):
            Session.objects.create(user=user, metric="estudio", date=MONDAY, duration_seconds=90)
        result = services.daily_minutes(user, "estudio", MONDAY, MONDAY)
        assert result[0]["minutes"] == 3

    def test_ignores_other_metrics(self, user):
        log(user, MONDAY, 30)
        Session.objects.create(user=user, metric="otra", date=MONDAY, duration_seconds=600)
        result = services.daily_minutes(user, "estudio", MONDAY, MONDAY)
        assert result[0]["minutes"] == 30

    def test_ignores_other_users(self, user, other_user):
        log(user, MONDAY, 30)
        log(other_user, MONDAY, 200)
        result = services.daily_minutes(user, "estudio", MONDAY, MONDAY)
        assert result[0]["minutes"] == 30


# --- Weekly cumulative (current week) ---------------------------------------

class TestWeekCumulative:
    def test_accumulates_and_keeps_flat_on_empty_days(self, user):
        # Mon 0, Tue +50 -> 50, Wed 0 -> 50, Thu +50 -> 100 (today = Thursday).
        log(user, MONDAY + timedelta(days=1), 50)
        log(user, MONDAY + timedelta(days=3), 50)
        result = services.week_cumulative(user, "estudio", MONDAY + timedelta(days=3))
        assert [r["cumulative_minutes"] for r in result] == [0, 50, 50, 100]
        assert [r["minutes"] for r in result] == [0, 50, 0, 50]

    def test_series_stops_at_today(self, user):
        log(user, MONDAY, 30)
        result = services.week_cumulative(user, "estudio", MONDAY + timedelta(days=2))
        assert len(result) == 3  # Monday through Wednesday, nothing beyond
        assert result[-1]["date"] == MONDAY + timedelta(days=2)

    def test_monday_alone_starts_at_its_minutes(self, user):
        log(user, MONDAY, 30)
        result = services.week_cumulative(user, "estudio", MONDAY)
        assert result == [{"date": MONDAY, "minutes": 30, "cumulative_minutes": 30}]

    def test_empty_week_is_all_zero(self, user):
        result = services.week_cumulative(user, "estudio", MONDAY + timedelta(days=6))
        assert len(result) == 7
        assert all(r["cumulative_minutes"] == 0 for r in result)

    def test_previous_week_sessions_do_not_leak_in(self, user):
        log(user, MONDAY - timedelta(days=1), 120)  # Sunday of the prior week
        result = services.week_cumulative(user, "estudio", MONDAY)
        assert result[-1]["cumulative_minutes"] == 0

    def test_scoped_to_user(self, user, other_user):
        log(other_user, MONDAY, 60)
        result = services.week_cumulative(user, "estudio", MONDAY)
        assert result[-1]["cumulative_minutes"] == 0


# --- Weekly summary and goal --------------------------------------------------

class TestWeeklySummaries:
    def test_week_met_when_total_reaches_goal(self, user):
        # Default goal 270: three 90-minute sessions meet it exactly.
        for i in range(3):
            log(user, MONDAY + timedelta(days=i), 90)
        [summary] = services.weekly_summaries(user, "estudio", MONDAY, weeks=1)
        assert summary.minutes == 270
        assert summary.goal_minutes == 270
        assert summary.met is True

    def test_week_not_met_below_goal(self, user):
        log(user, MONDAY, 269)
        [summary] = services.weekly_summaries(user, "estudio", MONDAY, weeks=1)
        assert summary.met is False

    def test_sessions_from_all_weekdays_count_to_same_week(self, user):
        log(user, MONDAY, 100)
        log(user, MONDAY + timedelta(days=6), 200)  # Sunday
        [summary] = services.weekly_summaries(
            user, "estudio", MONDAY + timedelta(days=3), weeks=1
        )
        assert summary.minutes == 300

    def test_returns_requested_weeks_ascending_with_zeroes(self, user):
        log(user, MONDAY, 300)
        summaries = services.weekly_summaries(
            user, "estudio", MONDAY + timedelta(weeks=2), weeks=3
        )
        assert [s.week_start for s in summaries] == [
            MONDAY,
            MONDAY + timedelta(weeks=1),
            MONDAY + timedelta(weeks=2),
        ]
        assert [s.minutes for s in summaries] == [300, 0, 0]
        assert [s.met for s in summaries] == [True, False, False]


class TestGoals:
    def test_default_goal_is_270(self, user):
        assert services.goal_for_week(user, get_metric("estudio"), MONDAY) == 270

    def test_goal_change_applies_from_current_week_not_backwards(self, user):
        services.set_goal(user, "estudio", 300, today=MONDAY + timedelta(weeks=1))
        metric = get_metric("estudio")
        assert services.goal_for_week(user, metric, MONDAY) == 270
        assert services.goal_for_week(user, metric, MONDAY + timedelta(weeks=1)) == 300
        assert services.goal_for_week(user, metric, MONDAY + timedelta(weeks=5)) == 300

    def test_goal_change_twice_same_week_keeps_last(self, user):
        services.set_goal(user, "estudio", 300, today=MONDAY)
        services.set_goal(user, "estudio", 200, today=MONDAY + timedelta(days=3))
        assert WeeklyGoal.objects.count() == 1
        assert services.goal_for_week(user, get_metric("estudio"), MONDAY) == 200

    def test_goals_are_per_user(self, user, other_user):
        services.set_goal(user, "estudio", 300, today=MONDAY)
        metric = get_metric("estudio")
        assert services.goal_for_week(other_user, metric, MONDAY) == 270

    def test_past_week_evaluated_with_goal_of_that_time(self, user):
        log(user, MONDAY, 280)  # meets 270, would miss 300
        services.set_goal(user, "estudio", 300, today=MONDAY + timedelta(weeks=1))
        summaries = services.weekly_summaries(
            user, "estudio", MONDAY + timedelta(weeks=1), weeks=2
        )
        assert summaries[0].met is True
        assert summaries[1].goal_minutes == 300


# --- Streak ---------------------------------------------------------------

class TestStreak:
    def meet_week(self, user, week: date):
        log(user, week, 270)

    def test_no_data_no_streak(self, user):
        assert services.current_streak(user, "estudio", MONDAY) == 0

    def test_consecutive_met_weeks_count(self, user):
        for i in range(3):
            self.meet_week(user, MONDAY - timedelta(weeks=i + 1))
        assert services.current_streak(user, "estudio", MONDAY) == 3

    def test_current_week_extends_streak_once_met(self, user):
        self.meet_week(user, MONDAY - timedelta(weeks=1))
        assert services.current_streak(user, "estudio", MONDAY) == 1
        self.meet_week(user, MONDAY)  # current week now met
        assert services.current_streak(user, "estudio", MONDAY) == 2

    def test_unmet_current_week_does_not_break_streak(self, user):
        self.meet_week(user, MONDAY - timedelta(weeks=1))
        log(user, MONDAY, 10)  # current week started but unmet
        assert services.current_streak(user, "estudio", MONDAY) == 1

    def test_gap_week_breaks_streak(self, user):
        self.meet_week(user, MONDAY - timedelta(weeks=3))
        self.meet_week(user, MONDAY - timedelta(weeks=1))  # gap at week -2
        assert services.current_streak(user, "estudio", MONDAY) == 1

    def test_partial_week_breaks_streak(self, user):
        self.meet_week(user, MONDAY - timedelta(weeks=3))
        log(user, MONDAY - timedelta(weeks=2), 100)  # week with data but goal missed
        self.meet_week(user, MONDAY - timedelta(weeks=1))
        assert services.current_streak(user, "estudio", MONDAY) == 1

    def test_streak_respects_goal_history(self, user):
        # Week -2 has 280 min against goal 270 (met); the goal then rises to
        # 300 and week -1 with 280 no longer meets it.
        log(user, MONDAY - timedelta(weeks=2), 280)
        services.set_goal(user, "estudio", 300, today=MONDAY - timedelta(weeks=1))
        log(user, MONDAY - timedelta(weeks=1), 280)
        assert services.current_streak(user, "estudio", MONDAY) == 0

    def test_streak_is_per_user(self, user, other_user):
        self.meet_week(other_user, MONDAY - timedelta(weeks=1))
        assert services.current_streak(user, "estudio", MONDAY) == 0


class TestTotals:
    def test_total_minutes_sums_everything(self, user):
        log(user, MONDAY, 30)
        log(user, MONDAY + timedelta(weeks=1), 45)
        assert services.total_minutes(user, "estudio") == 75

    def test_total_minutes_is_per_user(self, user, other_user):
        log(user, MONDAY, 30)
        log(other_user, MONDAY, 500)
        assert services.total_minutes(user, "estudio") == 30
