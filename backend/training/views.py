from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import (
    Exercise,
    ExerciseSubstitution,
    RunStatus,
    SetLog,
    SetPrescription,
    SubstitutionScope,
)
from .permissions import TrainingEnabled
from .serializers import (
    ExerciseSerializer,
    PerformanceSerializer,
    ProfileSerializer,
    ProgramDetailSerializer,
    ProgramRunSerializer,
    ProgramSerializer,
    ProgramVariantSerializer,
    RunStartSerializer,
    RunUpdateSerializer,
    ScheduledDaySerializer,
    SessionInputSerializer,
    SessionUpdateSerializer,
    SetLogInputSerializer,
    SetLogSerializer,
    SubstitutionInputSerializer,
    SubstitutionSerializer,
    WorkoutDayDetailSerializer,
    WorkoutSessionDetailSerializer,
    WorkoutSessionSerializer,
)


class TrainingView(APIView):
    """Base for every training endpoint: module gate always applied."""

    permission_classes = [IsAuthenticated, TrainingEnabled]


class ProfileView(TrainingView):
    """Preferences, plus a read-only view of what the user is running.

    `active_variant` / `active_program` are derived from the active run rather
    than stored: the run is the single answer to "what am I doing", and it is
    the only one that also knows since when.
    """

    def get(self, request):
        profile = request.user.training_profile
        run = services.active_run(request.user)
        variant = run.variant if run else None
        return Response(
            {
                "active_variant": (
                    ProgramVariantSerializer(variant).data if variant else None
                ),
                "active_program": variant.program.slug if variant else None,
                "active_run": run.pk if run else None,
                "weight_unit": profile.weight_unit,
            }
        )

    def put(self, request):
        serializer = ProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = request.user.training_profile
        data = serializer.validated_data

        if "weight_unit" in data:
            profile.weight_unit = data["weight_unit"]
        profile.save()
        return self.get(request)


class ProgramListView(TrainingView):
    def get(self, request):
        programs = services.accessible_programs(request.user).prefetch_related(
            "variants"
        )
        return Response(ProgramSerializer(programs, many=True).data)


class ProgramDetailView(TrainingView):
    def get(self, request, slug):
        program = get_object_or_404(
            services.accessible_programs(request.user).prefetch_related(
                "variants__phases__weeks__days"
            ),
            slug=slug,
        )
        return Response(ProgramDetailSerializer(program).data)


def run_payload(run, today):
    """A run plus everything the client needs to draw its calendar."""
    schedule = services.run_schedule(run)
    plan_week = services.current_plan_week(run, today)
    active = services.active_day(schedule, today, plan_week)
    data = ProgramRunSerializer(run).data
    data["ends_on"] = services.run_ends_on(run)
    data["total_weeks"] = services.total_weeks(run.variant)
    data["plan_week"] = plan_week
    data["adherence"] = services.adherence(schedule)
    data["schedule"] = ScheduledDaySerializer(schedule, many=True).data
    data["active_day"] = ScheduledDaySerializer(active).data if active else None
    return data


class RunListView(TrainingView):
    """The user's plans: at most one active, plus everything already run."""

    def get(self, request):
        runs = services.own_runs(request.user).select_related("variant__program")
        today = timezone.localdate()
        return Response(
            [
                run_payload(run, today)
                if run.status == RunStatus.ACTIVE
                else {
                    **ProgramRunSerializer(run).data,
                    "ends_on": services.run_ends_on(run),
                    "total_weeks": services.total_weeks(run.variant),
                }
                for run in runs
            ]
        )

    def post(self, request):
        serializer = RunStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        today = timezone.localdate()

        # 404, not 400: a variant of a program without access does not exist
        # for this user.
        variant = get_object_or_404(
            services.accessible_variants(request.user), pk=data["variant"]
        )
        run = services.start_run(
            request.user, variant, data.get("started_on") or today, today
        )
        return Response(run_payload(run, today), status=status.HTTP_201_CREATED)


class ActiveRunView(TrainingView):
    """What the dashboard asks for: the plan in progress, or nothing."""

    def get(self, request):
        run = services.active_run(request.user)
        if run is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(run_payload(run, timezone.localdate()))


class RunDetailView(TrainingView):
    def get(self, request, pk):
        run = get_object_or_404(services.own_runs(request.user), pk=pk)
        return Response(run_payload(run, timezone.localdate()))

    def patch(self, request, pk):
        run = get_object_or_404(services.own_runs(request.user), pk=pk)
        serializer = RunUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        today = timezone.localdate()

        if "started_on" in data:
            services.reschedule_run(run, data["started_on"])
        if "status" in data:
            services.finish_run(run, today, data["status"])
        return Response(run_payload(run, today))


class DayDetailView(TrainingView):
    """Prescription + where the day sits in the plan + what was logged on it.

    The session travels with the day on purpose: reopening a finished workout
    used to render a blank form because the client had no way to ask for it.
    """

    def get(self, request, pk):
        day = get_object_or_404(
            services.accessible_days(request.user)
            .select_related("week__phase__variant__program")
            .prefetch_related(
                "slots__exercise__equipment_required", "slots__sets"
            ),
            pk=pk,
        )
        run = services.active_run(request.user)
        in_plan = run is not None and day.week.phase.variant_id == run.variant_id
        session = services.session_for_day(request.user, day, run)

        scheduled_on = plan_week = None
        if in_plan:
            plan_week = services.plan_weeks(run.variant)[day.week_id]
            scheduled_on = services.scheduled_date(run.started_on, plan_week, day)

        slots = list(day.slots.all())
        # Both lookups below reach across weeks through the same map, so it is
        # built once here rather than twice inside them.
        siblings = services.sibling_slot_map(slots)
        # What the card is titled by, and what a logged set will record, are
        # the same lookup — resolved once for the whole day.
        substitutions = services.active_substitutions(
            request.user, slots, session, siblings=siblings
        )
        performed = services.performed_exercises(slots, substitutions)
        performances = services.last_performances(
            request.user,
            set(performed.values()),
            exclude_session=session,
        )
        last_performed = services.last_performed_exercises(
            request.user, slots, exclude_session=session, siblings=siblings
        )
        return Response(
            WorkoutDayDetailSerializer(
                day,
                context={
                    "session": session,
                    "in_active_plan": in_plan,
                    "plan_week": plan_week,
                    "scheduled_on": scheduled_on,
                    "substitutions": substitutions,
                    "performed_exercises": performed,
                    "last_performances": performances,
                    "last_performed_exercises": last_performed,
                },
            ).data
        )


class ExerciseHistoryView(TrainingView):
    """Every time the user performed this exercise, newest first.

    Keyed on SetLog.performed_exercise, so a substituted set counts for what
    was actually done — including the 13 imported rows where the prescribed
    and performed exercises differ.
    """

    DEFAULT_LIMIT = 20
    MAX_LIMIT = 100

    def get(self, request, pk):
        exercise = get_object_or_404(Exercise, pk=pk)
        try:
            limit = int(request.query_params.get("limit", self.DEFAULT_LIMIT))
        except ValueError:
            limit = self.DEFAULT_LIMIT
        limit = max(1, min(limit, self.MAX_LIMIT))
        sessions = services.exercise_history(request.user, exercise, limit)
        return Response(
            {
                "exercise": ExerciseSerializer(exercise).data,
                "sessions": PerformanceSerializer(sessions, many=True).data,
            }
        )


class SlotSubstitutionsView(TrainingView):
    """The substitution picker: query on open, persist on confirm."""

    def get(self, request, pk):
        slot = get_object_or_404(services.accessible_slots(request.user), pk=pk)
        grouped = services.substitution_candidates(slot)
        # `?session=` decides whether session-scoped swaps count: without a
        # session (a day not started yet) only program-scoped ones are in
        # force, which is the honest answer.
        session = None
        session_id = request.query_params.get("session")
        if session_id:
            session = services.own_sessions(request.user).filter(pk=session_id).first()
        active = services.active_substitutions(request.user, [slot], session).get(
            slot.pk
        )
        return Response(
            {
                "home": ExerciseSerializer(grouped["home"], many=True).data,
                "gym": ExerciseSerializer(grouped["gym"], many=True).data,
                "active": SubstitutionSerializer(active).data if active else None,
            }
        )

    def post(self, request, pk):
        slot = get_object_or_404(
            services.accessible_slots(request.user).select_related("day__week__phase"),
            pk=pk,
        )
        serializer = SubstitutionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        session = None
        if data.get("session") is not None:
            session = get_object_or_404(
                services.own_sessions(request.user), pk=data["session"]
            )
        elif data["scope"] == SubstitutionScope.SESSION:
            # "This session only" needs a session to be scoped to. Swapping an
            # exercise before logging the first set is the normal order, so the
            # session is opened here rather than leaving a row that is scoped to
            # nothing and silently never applies.
            session, _ = services.get_or_create_session(
                request.user, slot.day, timezone.localdate()
            )
        substitution = ExerciseSubstitution.objects.create(
            user=request.user,
            slot=slot,
            replacement=get_object_or_404(Exercise, pk=data["replacement"]),
            # The prescription, not what an earlier swap put in its place: a
            # program-scoped row follows the position only while the program
            # still prescribes this exercise there.
            original_exercise=slot.exercise,
            scope=data["scope"],
            session=session,
            reason=data.get("reason", ""),
        )
        return Response(
            SubstitutionSerializer(substitution).data, status=status.HTTP_201_CREATED
        )

    def delete(self, request, pk):
        """Back to the prescription.

        What gets deleted is whatever `active_substitutions` resolves for this
        slot, so you always undo the swap you were looking at. Removing a
        session-scoped row therefore uncovers the program-scoped one beneath
        it, which is the right answer: the one-off ends, the standing swap
        stays.
        """
        slot = get_object_or_404(services.accessible_slots(request.user), pk=pk)
        session = None
        session_id = request.query_params.get("session")
        if session_id:
            session = services.own_sessions(request.user).filter(pk=session_id).first()
        substitution = services.active_substitutions(
            request.user, [slot], session
        ).get(slot.pk)
        if substitution is None:
            raise Http404("No substitution in force for this slot.")
        substitution.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionListView(TrainingView):
    def get(self, request):
        sessions = services.own_sessions(request.user).select_related(
            "day"
        ).order_by("-performed_on", "-id")
        day = request.query_params.get("day")
        if day:
            sessions = sessions.filter(day_id=day)
        return Response(WorkoutSessionSerializer(sessions, many=True).data)

    def post(self, request):
        """Idempotent: opening the same day twice reuses its session.

        The old unconditional create is what produced duplicate sessions for
        one day+week every time a workout was reopened.
        """
        serializer = SessionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        day = get_object_or_404(
            services.accessible_days(request.user).select_related("week__phase"),
            pk=serializer.validated_data["day"],
        )
        session, created = services.get_or_create_session(
            request.user, day, timezone.localdate()
        )
        return Response(
            WorkoutSessionSerializer(session).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class SessionDetailView(TrainingView):
    def get(self, request, pk):
        session = get_object_or_404(
            services.own_sessions(request.user).select_related("day").prefetch_related(
                "logs__performed_exercise"
            ),
            pk=pk,
        )
        return Response(WorkoutSessionDetailSerializer(session).data)

    def patch(self, request, pk):
        session = get_object_or_404(services.own_sessions(request.user), pk=pk)
        serializer = SessionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "notes" in data:
            session.notes = data["notes"]
        if "completed" in data:
            session.completed_at = timezone.now() if data["completed"] else None
        session.save()
        return self.get(request, pk)


class SessionLogsView(TrainingView):
    def post(self, request, pk):
        session = get_object_or_404(services.own_sessions(request.user), pk=pk)
        serializer = SetLogInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        slot = get_object_or_404(
            services.accessible_slots(request.user), pk=data["slot"]
        )
        # Scope-aware: a swap made for another session must not follow the
        # exercise into this one.
        substitution = services.active_substitutions(
            request.user, [slot], session
        ).get(slot.pk)
        performed = substitution.replacement if substitution else slot.exercise
        log = SetLog.objects.create(
            session=session,
            prescription=SetPrescription.objects.filter(
                slot=slot, set_number=data["set_number"]
            ).first(),
            performed_exercise=performed,
            was_substituted=substitution is not None,
            set_number=data["set_number"],
            weight=data.get("weight"),
            weight_basis=data.get("weight_basis", "total"),
            reps=data.get("reps"),
            rpe=data.get("rpe"),
            rir=data.get("rir"),
        )
        return Response(SetLogSerializer(log).data, status=status.HTTP_201_CREATED)


class SessionLogDetailView(TrainingView):
    """Un-logging a set: the toggle's DELETE side."""

    def delete(self, request, pk, log_id):
        session = get_object_or_404(services.own_sessions(request.user), pk=pk)
        log = get_object_or_404(SetLog, session=session, pk=log_id)
        log.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
