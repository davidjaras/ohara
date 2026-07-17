"""Business-logic tests: timer, aggregations, goal and streak."""

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


def log(day: date, minutes: int, metric: str = "estudio") -> Session:
    return services.log_manual_session(metric, day, minutes)


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
    def test_full_flow_with_pauses_accumulates_only_running_time(self):
        t0 = dt(2026, 7, 6, 10, 0, 0)
        services.start_timer("estudio", t0)
        services.pause_timer("estudio", t0 + timedelta(minutes=10))
        services.resume_timer("estudio", t0 + timedelta(minutes=25))
        services.pause_timer("estudio", t0 + timedelta(minutes=40))
        services.resume_timer("estudio", t0 + timedelta(minutes=50))
        session = services.finish_timer("estudio", t0 + timedelta(minutes=60), note="repaso")

        # Ran 10 + 15 + 10 minutes; the pauses (15 + 10) don't count.
        assert session.duration_seconds == 35 * 60
        assert session.note == "repaso"
        assert session.started_at == t0
        assert session.ended_at == t0 + timedelta(minutes=60)
        assert not ActiveTimer.objects.exists()

    def test_elapsed_while_paused_does_not_grow(self):
        t0 = dt(2026, 7, 6, 10, 0, 0)
        services.start_timer("estudio", t0)
        timer = services.pause_timer("estudio", t0 + timedelta(minutes=5))
        assert timer.elapsed_seconds(t0 + timedelta(hours=3)) == 5 * 60

    def test_session_attributed_to_start_day_across_midnight(self, settings):
        settings.TIME_ZONE = "UTC"
        t0 = dt(2026, 7, 6, 23, 30, 0)
        services.start_timer("estudio", t0)
        session = services.finish_timer("estudio", t0 + timedelta(hours=1))
        assert session.date == date(2026, 7, 6)

    def test_cannot_start_twice(self):
        services.start_timer("estudio", dt(2026, 7, 6, 10, 0))
        with pytest.raises(services.TimerError):
            services.start_timer("estudio", dt(2026, 7, 6, 11, 0))

    def test_cannot_pause_paused_or_resume_running(self):
        t0 = dt(2026, 7, 6, 10, 0)
        services.start_timer("estudio", t0)
        with pytest.raises(services.TimerError):
            services.resume_timer("estudio", t0 + timedelta(minutes=1))
        services.pause_timer("estudio", t0 + timedelta(minutes=2))
        with pytest.raises(services.TimerError):
            services.pause_timer("estudio", t0 + timedelta(minutes=3))

    def test_operations_without_timer_fail(self):
        for op in (services.pause_timer, services.resume_timer, services.finish_timer):
            with pytest.raises(services.TimerError):
                op("estudio", dt(2026, 7, 6, 10, 0))

    def test_discard_deletes_without_creating_session(self):
        services.start_timer("estudio", dt(2026, 7, 6, 10, 0))
        services.discard_timer("estudio")
        assert not ActiveTimer.objects.exists()
        assert not Session.objects.exists()

    def test_start_rejects_unknown_and_measurement_metrics(self):
        with pytest.raises(ValueError):
            services.start_timer("inventada", dt(2026, 7, 6, 10, 0))


# --- Manual entry ---------------------------------------------------------

class TestManualLog:
    def test_creates_session_without_timestamps(self):
        session = log(MONDAY, 45)
        assert session.duration_seconds == 45 * 60
        assert session.started_at is None

    def test_rejects_non_positive_minutes(self):
        with pytest.raises(ValueError):
            services.log_manual_session("estudio", MONDAY, 0)


# --- Daily aggregation -------------------------------------------------------

class TestDailyMinutes:
    def test_sums_per_day_and_fills_zero_days(self):
        log(MONDAY, 30)
        log(MONDAY, 15)
        log(MONDAY + timedelta(days=2), 60)
        result = services.daily_minutes("estudio", MONDAY, MONDAY + timedelta(days=3))
        assert [r["minutes"] for r in result] == [45, 0, 60, 0]
        assert result[0]["date"] == MONDAY

    def test_seconds_are_summed_before_flooring_to_minutes(self):
        # 90s + 90s = 3 min; flooring per session would give 1+1 = 2.
        for _ in range(2):
            Session.objects.create(metric="estudio", date=MONDAY, duration_seconds=90)
        result = services.daily_minutes("estudio", MONDAY, MONDAY)
        assert result[0]["minutes"] == 3

    def test_ignores_other_metrics(self):
        log(MONDAY, 30)
        Session.objects.create(metric="otra", date=MONDAY, duration_seconds=600)
        result = services.daily_minutes("estudio", MONDAY, MONDAY)
        assert result[0]["minutes"] == 30


# --- Weekly summary and goal --------------------------------------------------

class TestWeeklySummaries:
    def test_week_met_when_total_reaches_goal(self):
        # Default goal 270: three 90-minute sessions meet it exactly.
        for i in range(3):
            log(MONDAY + timedelta(days=i), 90)
        [summary] = services.weekly_summaries("estudio", MONDAY, weeks=1)
        assert summary.minutes == 270
        assert summary.goal_minutes == 270
        assert summary.met is True

    def test_week_not_met_below_goal(self):
        log(MONDAY, 269)
        [summary] = services.weekly_summaries("estudio", MONDAY, weeks=1)
        assert summary.met is False

    def test_sessions_from_all_weekdays_count_to_same_week(self):
        log(MONDAY, 100)
        log(MONDAY + timedelta(days=6), 200)  # Sunday
        [summary] = services.weekly_summaries("estudio", MONDAY + timedelta(days=3), weeks=1)
        assert summary.minutes == 300

    def test_returns_requested_weeks_ascending_with_zeroes(self):
        log(MONDAY, 300)
        summaries = services.weekly_summaries("estudio", MONDAY + timedelta(weeks=2), weeks=3)
        assert [s.week_start for s in summaries] == [
            MONDAY,
            MONDAY + timedelta(weeks=1),
            MONDAY + timedelta(weeks=2),
        ]
        assert [s.minutes for s in summaries] == [300, 0, 0]
        assert [s.met for s in summaries] == [True, False, False]


class TestGoals:
    def test_default_goal_is_270(self):
        assert services.goal_for_week(get_metric("estudio"), MONDAY) == 270

    def test_goal_change_applies_from_current_week_not_backwards(self):
        services.set_goal("estudio", 300, today=MONDAY + timedelta(weeks=1))
        metric = get_metric("estudio")
        assert services.goal_for_week(metric, MONDAY) == 270
        assert services.goal_for_week(metric, MONDAY + timedelta(weeks=1)) == 300
        assert services.goal_for_week(metric, MONDAY + timedelta(weeks=5)) == 300

    def test_goal_change_twice_same_week_keeps_last(self):
        services.set_goal("estudio", 300, today=MONDAY)
        services.set_goal("estudio", 200, today=MONDAY + timedelta(days=3))
        assert WeeklyGoal.objects.count() == 1
        assert services.goal_for_week(get_metric("estudio"), MONDAY) == 200

    def test_past_week_evaluated_with_goal_of_that_time(self):
        log(MONDAY, 280)  # meets 270, would miss 300
        services.set_goal("estudio", 300, today=MONDAY + timedelta(weeks=1))
        summaries = services.weekly_summaries("estudio", MONDAY + timedelta(weeks=1), weeks=2)
        assert summaries[0].met is True
        assert summaries[1].goal_minutes == 300


# --- Streak -------------------------------------------------------------------

class TestStreak:
    def meet_week(self, week: date):
        log(week, 270)

    def test_no_data_no_streak(self):
        assert services.current_streak("estudio", MONDAY) == 0

    def test_consecutive_met_weeks_count(self):
        for i in range(3):
            self.meet_week(MONDAY - timedelta(weeks=i + 1))
        assert services.current_streak("estudio", MONDAY) == 3

    def test_current_week_extends_streak_once_met(self):
        self.meet_week(MONDAY - timedelta(weeks=1))
        assert services.current_streak("estudio", MONDAY) == 1
        self.meet_week(MONDAY)  # current week now met
        assert services.current_streak("estudio", MONDAY) == 2

    def test_unmet_current_week_does_not_break_streak(self):
        self.meet_week(MONDAY - timedelta(weeks=1))
        log(MONDAY, 10)  # current week started but unmet
        assert services.current_streak("estudio", MONDAY) == 1

    def test_gap_week_breaks_streak(self):
        self.meet_week(MONDAY - timedelta(weeks=3))
        self.meet_week(MONDAY - timedelta(weeks=1))  # gap at week -2
        assert services.current_streak("estudio", MONDAY) == 1

    def test_partial_week_breaks_streak(self):
        self.meet_week(MONDAY - timedelta(weeks=3))
        log(MONDAY - timedelta(weeks=2), 100)  # week with data but goal missed
        self.meet_week(MONDAY - timedelta(weeks=1))
        assert services.current_streak("estudio", MONDAY) == 1

    def test_streak_respects_goal_history(self):
        # Week -2 has 280 min against goal 270 (met); the goal then rises to
        # 300 and week -1 with 280 no longer meets it.
        log(MONDAY - timedelta(weeks=2), 280)
        services.set_goal("estudio", 300, today=MONDAY - timedelta(weeks=1))
        log(MONDAY - timedelta(weeks=1), 280)
        assert services.current_streak("estudio", MONDAY) == 0


class TestTotals:
    def test_total_minutes_sums_everything(self):
        log(MONDAY, 30)
        log(MONDAY + timedelta(weeks=1), 45)
        assert services.total_minutes("estudio") == 75
