"""Business-logic tests: timer, aggregations, goal, streak and cumulative."""

from datetime import date, datetime, timedelta, timezone as dt_timezone

import pytest

from tracker import services
from tracker.metrics import get_metric
from tracker.models import ActiveTimer, Session, UserPreference, WeeklyGoal

pytestmark = pytest.mark.django_db

UTC = dt_timezone.utc


def dt(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


# Monday July 6, 2026 anchors the weeks used in these tests.
MONDAY = date(2026, 7, 6)


def log(user, day: date, minutes: int, metric: str = "estudio") -> Session:
    # `day` doubles as "today": logging on the day itself is always in the past.
    return services.log_manual_session(user, metric, day, minutes, day)


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

    def test_session_row_is_dated_by_its_start_day(self, user, settings):
        # The row keeps the start day; the time itself is split across the days
        # it spans when aggregating (see TestDaySegments).
        settings.TIME_ZONE = "UTC"
        t0 = dt(2026, 7, 6, 23, 30, 0)
        services.start_timer(user, "estudio", t0)
        session = services.finish_timer(user, "estudio", t0 + timedelta(hours=1))
        assert session.date == date(2026, 7, 6)

    def test_forgotten_timer_is_clamped_to_a_full_day(self, user):
        t0 = dt(2026, 7, 6, 10, 0, 0)
        services.start_timer(user, "estudio", t0)
        session = services.finish_timer(user, "estudio", t0 + timedelta(days=3))
        assert session.duration_seconds == 24 * 60 * 60
        assert session.ended_at == t0 + timedelta(days=1)

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


class TestPlannedTimer:
    def test_start_stores_the_planned_duration(self, user):
        timer = services.start_timer(user, "estudio", dt(2026, 7, 6, 10, 0), planned_minutes=50)
        assert timer.planned_duration_seconds == 50 * 60

    def test_start_without_plan_is_open_ended(self, user):
        timer = services.start_timer(user, "estudio", dt(2026, 7, 6, 10, 0))
        assert timer.planned_duration_seconds is None

    @pytest.mark.parametrize("minutes", [0, -5, 1441])
    def test_start_rejects_plans_outside_a_day(self, user, minutes):
        with pytest.raises(ValueError):
            services.start_timer(user, "estudio", dt(2026, 7, 6, 10, 0), planned_minutes=minutes)

    def test_extend_moves_the_target(self, user):
        t0 = dt(2026, 7, 6, 10, 0)
        services.start_timer(user, "estudio", t0, planned_minutes=50)
        timer = services.extend_timer(user, "estudio", t0 + timedelta(minutes=50), 15)
        assert timer.planned_duration_seconds == 65 * 60

    def test_extend_requires_a_planned_session(self, user):
        t0 = dt(2026, 7, 6, 10, 0)
        services.start_timer(user, "estudio", t0)
        with pytest.raises(services.TimerError):
            services.extend_timer(user, "estudio", t0 + timedelta(minutes=10), 15)

    def test_extend_cannot_push_the_plan_beyond_a_day(self, user):
        t0 = dt(2026, 7, 6, 10, 0)
        services.start_timer(user, "estudio", t0, planned_minutes=1440)
        with pytest.raises(ValueError):
            services.extend_timer(user, "estudio", t0 + timedelta(minutes=10), 1)


# --- Auto-close and repair ---------------------------------------------------

class TestAutoClose:
    @pytest.fixture(autouse=True)
    def grace(self, settings):
        settings.TIMER_GRACE_SECONDS = 300

    T0 = dt(2026, 7, 6, 10, 0)

    def start_planned(self, user, minutes=50):
        return services.start_timer(user, "estudio", self.T0, planned_minutes=minutes)

    def test_nothing_happens_before_the_plan_is_met(self, user):
        self.start_planned(user)
        assert services.finalize_expired_timer(user, "estudio", self.T0 + timedelta(minutes=49)) is None
        assert ActiveTimer.objects.exists()

    def test_nothing_happens_during_the_grace(self, user):
        self.start_planned(user)
        at = self.T0 + timedelta(minutes=50, seconds=299)
        assert services.finalize_expired_timer(user, "estudio", at) is None
        assert ActiveTimer.objects.exists()

    def test_closes_at_exactly_the_planned_duration_after_grace(self, user):
        self.start_planned(user)
        session = services.finalize_expired_timer(
            user, "estudio", self.T0 + timedelta(minutes=55)
        )
        assert session.duration_seconds == 50 * 60
        assert session.estimated_duration_seconds == 50 * 60
        assert session.close_reason == Session.CLOSE_PLANNED_END
        assert session.ended_at == self.T0 + timedelta(minutes=50)
        assert session.started_at == self.T0
        assert session.needs_review is True
        assert not ActiveTimer.objects.exists()

    def test_days_later_still_truncates_to_the_plan(self, user):
        self.start_planned(user)
        session = services.finalize_expired_timer(user, "estudio", self.T0 + timedelta(days=3))
        assert session.duration_seconds == 50 * 60
        assert session.ended_at == self.T0 + timedelta(minutes=50)

    def test_pauses_shift_the_crossing_instant(self, user):
        self.start_planned(user)
        services.pause_timer(user, "estudio", self.T0 + timedelta(minutes=10))
        services.resume_timer(user, "estudio", self.T0 + timedelta(minutes=30))
        # 10 min accumulated; the remaining 40 run from 10:30, crossing at 11:10.
        session = services.finalize_expired_timer(user, "estudio", self.T0 + timedelta(hours=2))
        assert session.duration_seconds == 50 * 60
        assert session.ended_at == self.T0 + timedelta(minutes=70)

    def test_paused_timer_never_expires(self, user):
        self.start_planned(user)
        services.pause_timer(user, "estudio", self.T0 + timedelta(minutes=10))
        assert services.finalize_expired_timer(user, "estudio", self.T0 + timedelta(days=2)) is None
        assert ActiveTimer.objects.exists()

    def test_open_ended_timer_with_reminders_off_is_left_alone(self, user):
        UserPreference.objects.create(user=user, reminder_minutes=None)
        services.start_timer(user, "estudio", self.T0)
        assert services.finalize_expired_timer(user, "estudio", self.T0 + timedelta(hours=10)) is None

    def test_extension_moves_the_deadline(self, user):
        self.start_planned(user)
        services.extend_timer(user, "estudio", self.T0 + timedelta(minutes=50), 30)
        assert services.finalize_expired_timer(user, "estudio", self.T0 + timedelta(minutes=60)) is None
        session = services.finalize_expired_timer(user, "estudio", self.T0 + timedelta(minutes=90))
        assert session.duration_seconds == 80 * 60

    def test_without_timer_returns_none(self, user):
        assert services.finalize_expired_timer(user, "estudio", self.T0) is None


class TestIdleClose:
    """No-limit sessions: two silent reminder intervals close the timer,
    truncated to the last confirmed interaction."""

    T0 = dt(2026, 7, 6, 10, 0)

    def start(self, user):
        # Default preference: 30-minute reminders, so the deadline sits at
        # the last confirmation + 60 minutes.
        return services.start_timer(user, "estudio", self.T0)

    def test_start_snapshots_the_preference(self, user):
        UserPreference.objects.create(user=user, reminder_minutes=45)
        timer = self.start(user)
        assert timer.reminder_interval_seconds == 45 * 60

    def test_start_defaults_to_thirty_minutes_without_preference(self, user):
        assert self.start(user).reminder_interval_seconds == 30 * 60

    def test_planned_sessions_take_no_reminders(self, user):
        timer = services.start_timer(user, "estudio", self.T0, planned_minutes=50)
        assert timer.reminder_interval_seconds is None

    def test_preference_change_does_not_move_a_running_deadline(self, user):
        pref = UserPreference.objects.create(user=user, reminder_minutes=30)
        timer = self.start(user)
        pref.reminder_minutes = 120
        pref.save()
        timer.refresh_from_db()
        assert timer.reminder_interval_seconds == 30 * 60

    def test_not_due_before_two_silent_intervals(self, user):
        self.start(user)
        at = self.T0 + timedelta(minutes=59)
        assert services.finalize_expired_timer(user, "estudio", at) is None

    def test_start_then_vanish_closes_at_zero(self, user):
        self.start(user)
        session = services.finalize_expired_timer(user, "estudio", self.T0 + timedelta(minutes=60))
        assert session.duration_seconds == 0
        assert session.ended_at == self.T0
        assert session.close_reason == Session.CLOSE_IDLE_TIMEOUT
        assert session.estimated_duration_seconds == 0
        assert session.idle_threshold_seconds == 30 * 60
        assert session.needs_review is True
        assert not ActiveTimer.objects.exists()

    def test_checkin_pushes_the_deadline(self, user):
        self.start(user)
        services.checkin_timer(user, "estudio", self.T0 + timedelta(minutes=50))
        at = self.T0 + timedelta(minutes=109)
        assert services.finalize_expired_timer(user, "estudio", at) is None
        session = services.finalize_expired_timer(user, "estudio", self.T0 + timedelta(minutes=110))
        # Truncated to the last check-in, never to the threshold.
        assert session.duration_seconds == 50 * 60
        assert session.ended_at == self.T0 + timedelta(minutes=50)

    def test_pause_and_resume_count_as_confirmations(self, user):
        self.start(user)
        services.pause_timer(user, "estudio", self.T0 + timedelta(minutes=10))
        services.resume_timer(user, "estudio", self.T0 + timedelta(minutes=20))
        # Confirmed at resume: 10 active minutes. Due 60 active minutes later.
        session = services.finalize_expired_timer(user, "estudio", self.T0 + timedelta(minutes=80))
        assert session.duration_seconds == 10 * 60
        assert session.ended_at == self.T0 + timedelta(minutes=20)

    def test_paused_timer_never_expires(self, user):
        self.start(user)
        services.pause_timer(user, "estudio", self.T0 + timedelta(minutes=10))
        assert services.finalize_expired_timer(user, "estudio", self.T0 + timedelta(days=2)) is None
        assert ActiveTimer.objects.exists()


class TestReviewSession:
    T0 = dt(2026, 7, 6, 10, 0)
    NOW = dt(2026, 7, 6, 12, 0)

    def auto_closed(self, user) -> Session:
        services.start_timer(user, "estudio", self.T0, planned_minutes=50)
        return services.finalize_expired_timer(user, "estudio", self.T0 + timedelta(hours=1))

    def test_confirm_marks_reviewed_and_keeps_the_estimate(self, user):
        session = self.auto_closed(user)
        reviewed = services.review_session(user, session.pk, self.NOW, "confirm")
        assert reviewed.reviewed_at == self.NOW
        assert reviewed.duration_seconds == 50 * 60
        assert reviewed.needs_review is False

    def test_confirm_can_attach_a_note(self, user):
        session = self.auto_closed(user)
        reviewed = services.review_session(user, session.pk, self.NOW, "confirm", note="repaso")
        assert reviewed.note == "repaso"

    def test_adjust_moves_the_end_and_recomputes_the_duration(self, user):
        session = self.auto_closed(user)
        reviewed = services.review_session(
            user, session.pk, self.NOW, "adjust", ended_at=self.T0 + timedelta(minutes=30)
        )
        assert reviewed.duration_seconds == 30 * 60
        assert reviewed.started_at == self.T0
        assert reviewed.ended_at == self.T0 + timedelta(minutes=30)
        # The original estimate stays frozen for calibration.
        assert reviewed.estimated_duration_seconds == 50 * 60
        assert reviewed.needs_review is False

    def test_adjust_requires_an_end_time(self, user):
        session = self.auto_closed(user)
        with pytest.raises(ValueError):
            services.review_session(user, session.pk, self.NOW, "adjust")

    def test_adjust_rejects_an_end_before_the_start(self, user):
        session = self.auto_closed(user)
        with pytest.raises(ValueError):
            services.review_session(
                user, session.pk, self.NOW, "adjust", ended_at=self.T0 - timedelta(minutes=1)
            )

    def test_adjust_rejects_a_future_end(self, user):
        session = self.auto_closed(user)
        with pytest.raises(ValueError):
            services.review_session(
                user, session.pk, self.NOW, "adjust", ended_at=self.NOW + timedelta(minutes=1)
            )

    def test_reviewing_twice_fails(self, user):
        session = self.auto_closed(user)
        services.review_session(user, session.pk, self.NOW, "confirm")
        with pytest.raises(ValueError):
            services.review_session(user, session.pk, self.NOW, "confirm")

    def test_a_measured_session_cannot_be_reviewed(self, user):
        session = log(user, MONDAY, 30)
        with pytest.raises(ValueError):
            services.review_session(user, session.pk, self.NOW, "confirm")

    def test_cannot_review_another_users_session(self, user, other_user):
        session = self.auto_closed(user)
        with pytest.raises(LookupError):
            services.review_session(other_user, session.pk, self.NOW, "confirm")


# --- Day attribution ---------------------------------------------------------

@pytest.fixture
def utc(settings):
    """Pin the local timezone so midnight is at a known instant."""
    settings.TIME_ZONE = "UTC"


def timed(user, start: datetime, end: datetime, seconds: int | None = None) -> Session:
    """A timed session; `seconds` defaults to the whole wall-clock span."""
    return Session.objects.create(
        user=user,
        metric="estudio",
        date=services.local_date(start),
        duration_seconds=seconds if seconds is not None else int((end - start).total_seconds()),
        started_at=start,
        ended_at=end,
    )


class TestDaySegments:
    def test_manual_entry_lands_entirely_on_its_date(self, user):
        session = log(user, MONDAY, 45)
        assert services.day_segments(session) == [(MONDAY, 45 * 60)]

    def test_session_within_one_day_is_not_split(self, user, utc):
        session = timed(user, dt(2026, 7, 6, 10, 0), dt(2026, 7, 6, 11, 0))
        assert services.day_segments(session) == [(MONDAY, 3600)]

    def test_session_across_midnight_is_split_by_day(self, user, utc):
        session = timed(user, dt(2026, 7, 6, 23, 30), dt(2026, 7, 7, 0, 30))
        assert services.day_segments(session) == [
            (MONDAY, 30 * 60),
            (MONDAY + timedelta(days=1), 30 * 60),
        ]

    def test_pauses_are_spread_proportionally(self, user, utc):
        # 23:00 -> 01:00 of wall clock, but only 60 min actually counted.
        session = timed(user, dt(2026, 7, 6, 23, 0), dt(2026, 7, 7, 1, 0), seconds=60 * 60)
        assert services.day_segments(session) == [
            (MONDAY, 30 * 60),
            (MONDAY + timedelta(days=1), 30 * 60),
        ]

    def test_segments_always_add_up_to_the_duration(self, user, utc):
        # An odd duration forces rounding: the remainder goes to the last day.
        session = timed(user, dt(2026, 7, 6, 23, 0), dt(2026, 7, 7, 2, 0), seconds=3601)
        segments = services.day_segments(session)
        assert sum(seconds for _day, seconds in segments) == 3601

    def test_multi_day_session_covers_every_day(self, user, utc):
        session = timed(user, dt(2026, 7, 6, 12, 0), dt(2026, 7, 8, 12, 0))
        assert [day for day, _seconds in services.day_segments(session)] == [
            MONDAY,
            MONDAY + timedelta(days=1),
            MONDAY + timedelta(days=2),
        ]


# --- Manual entry ---------------------------------------------------------

class TestManualLog:
    def test_creates_session_without_timestamps(self, user):
        session = log(user, MONDAY, 45)
        assert session.duration_seconds == 45 * 60
        assert session.started_at is None

    def test_rejects_non_positive_minutes(self, user):
        with pytest.raises(ValueError):
            services.log_manual_session(user, "estudio", MONDAY, 0, MONDAY)

    def test_rejects_more_minutes_than_a_day_has(self, user):
        with pytest.raises(ValueError):
            services.log_manual_session(user, "estudio", MONDAY, 1441, MONDAY)

    def test_rejects_future_date(self, user):
        with pytest.raises(ValueError):
            services.log_manual_session(user, "estudio", MONDAY + timedelta(days=1), 30, MONDAY)

    def test_rejects_entry_that_overflows_the_day(self, user):
        log(user, MONDAY, 1400)
        with pytest.raises(ValueError):
            services.log_manual_session(user, "estudio", MONDAY, 41, MONDAY)

    def test_accepts_the_minutes_that_still_fit(self, user):
        log(user, MONDAY, 1400)
        assert log(user, MONDAY, 40).duration_seconds == 40 * 60

    def test_day_total_counts_time_spilled_from_the_previous_day(self, user, utc):
        timed(user, dt(2026, 7, 6, 23, 0), dt(2026, 7, 7, 23, 0))  # 23 h on Tuesday
        tuesday = MONDAY + timedelta(days=1)
        with pytest.raises(ValueError):
            services.log_manual_session(user, "estudio", tuesday, 61, tuesday)


class TestUpdateSession:
    def test_edits_date_minutes_and_note(self, user):
        session = log(user, MONDAY, 30)
        updated = services.update_session(
            user, session.pk, MONDAY, day=MONDAY, minutes=45, note="repaso"
        )
        assert updated.duration_seconds == 45 * 60
        assert updated.note == "repaso"

    def test_excludes_itself_from_the_day_total(self, user):
        session = log(user, MONDAY, 1400)
        assert services.update_session(user, session.pk, MONDAY, minutes=1440).duration_seconds

    def test_still_rejects_overflowing_the_day(self, user):
        log(user, MONDAY, 1000)
        session = log(user, MONDAY, 400)
        with pytest.raises(ValueError):
            services.update_session(user, session.pk, MONDAY, minutes=441)

    def test_retiming_a_timed_session_drops_its_timestamps(self, user, utc):
        session = timed(user, dt(2026, 7, 6, 10, 0), dt(2026, 7, 6, 11, 0))
        updated = services.update_session(user, session.pk, MONDAY, minutes=30)
        assert updated.started_at is None and updated.ended_at is None

    def test_editing_only_the_note_keeps_the_timestamps(self, user, utc):
        session = timed(user, dt(2026, 7, 6, 10, 0), dt(2026, 7, 6, 11, 0))
        updated = services.update_session(user, session.pk, MONDAY, note="cálculo")
        assert updated.started_at is not None
        assert updated.duration_seconds == 3600

    def test_cannot_edit_another_users_session(self, user, other_user):
        session = log(user, MONDAY, 30)
        with pytest.raises(LookupError):
            services.update_session(other_user, session.pk, MONDAY, minutes=10)


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

    def test_session_across_midnight_counts_on_both_days(self, user, utc):
        timed(user, dt(2026, 7, 6, 23, 30), dt(2026, 7, 7, 0, 30))
        result = services.daily_minutes(user, "estudio", MONDAY, MONDAY + timedelta(days=1))
        assert [r["minutes"] for r in result] == [30, 30]

    def test_time_spilled_into_the_range_is_counted(self, user, utc):
        # The session started the day before the range and reaches into it.
        timed(user, dt(2026, 7, 6, 23, 30), dt(2026, 7, 7, 0, 30))
        tuesday = MONDAY + timedelta(days=1)
        result = services.daily_minutes(user, "estudio", tuesday, tuesday)
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

    def test_session_from_sunday_into_monday_splits_across_weeks(self, user, utc):
        sunday_night = dt(2026, 7, 12, 23, 30)  # Sunday of MONDAY's week
        timed(user, sunday_night, sunday_night + timedelta(hours=1))
        summaries = services.weekly_summaries(
            user, "estudio", MONDAY + timedelta(weeks=1), weeks=2
        )
        assert [s.minutes for s in summaries] == [30, 30]

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

    def test_rejects_goal_beyond_the_minutes_a_week_has(self, user):
        with pytest.raises(ValueError):
            services.set_goal(user, "estudio", 10081, today=MONDAY)

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
