from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Exercise, ExerciseSubstitution, SetLog, SetPrescription, WorkoutSession
from .permissions import TrainingEnabled
from .serializers import (
    ExerciseSerializer,
    ProfileSerializer,
    ProgramDetailSerializer,
    ProgramSerializer,
    ProgramVariantSerializer,
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
    """The user's training profile: active variant and weight unit."""

    def get(self, request):
        profile = request.user.training_profile
        variant = profile.active_variant
        return Response(
            {
                "active_variant": (
                    ProgramVariantSerializer(variant).data if variant else None
                ),
                "active_program": variant.program.slug if variant else None,
                "weight_unit": profile.weight_unit,
            }
        )

    def put(self, request):
        serializer = ProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = request.user.training_profile
        data = serializer.validated_data

        if "active_variant" in data:
            variant_id = data["active_variant"]
            if variant_id is None:
                profile.active_variant = None
            else:
                # 404, not 400: a variant of a program without access does
                # not exist for this user.
                profile.active_variant = get_object_or_404(
                    services.accessible_variants(request.user), pk=variant_id
                )
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


class DayDetailView(TrainingView):
    def get(self, request, pk):
        day = get_object_or_404(
            services.accessible_days(request.user).prefetch_related(
                "slots__exercise__equipment_required", "slots__sets"
            ),
            pk=pk,
        )
        return Response(WorkoutDayDetailSerializer(day).data)


class SlotSubstitutionsView(TrainingView):
    """The substitution picker: query on open, persist on confirm."""

    def get(self, request, pk):
        slot = get_object_or_404(services.accessible_slots(request.user), pk=pk)
        grouped = services.substitution_candidates(slot)
        active = (
            ExerciseSubstitution.objects.filter(user=request.user, slot=slot)
            .order_by("-created_at")
            .first()
        )
        return Response(
            {
                "home": ExerciseSerializer(grouped["home"], many=True).data,
                "gym": ExerciseSerializer(grouped["gym"], many=True).data,
                "active": SubstitutionSerializer(active).data if active else None,
            }
        )

    def post(self, request, pk):
        slot = get_object_or_404(services.accessible_slots(request.user), pk=pk)
        serializer = SubstitutionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        session = None
        if data.get("session") is not None:
            session = get_object_or_404(
                services.own_sessions(request.user), pk=data["session"]
            )
        substitution = ExerciseSubstitution.objects.create(
            user=request.user,
            slot=slot,
            replacement=get_object_or_404(Exercise, pk=data["replacement"]),
            scope=data["scope"],
            session=session,
            reason=data.get("reason", ""),
        )
        return Response(
            SubstitutionSerializer(substitution).data, status=status.HTTP_201_CREATED
        )


class SessionListView(TrainingView):
    def get(self, request):
        sessions = services.own_sessions(request.user).select_related(
            "day"
        ).order_by("-performed_on", "-id")
        return Response(WorkoutSessionSerializer(sessions, many=True).data)

    def post(self, request):
        serializer = SessionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        day = get_object_or_404(
            services.accessible_days(request.user), pk=data["day"]
        )
        session = WorkoutSession.objects.create(
            user=request.user,
            day=day,
            week_number=data["week_number"],
            performed_on=data.get("performed_on") or timezone.localdate(),
            notes=data.get("notes", ""),
        )
        return Response(
            WorkoutSessionSerializer(session).data, status=status.HTTP_201_CREATED
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
        substitution = (
            ExerciseSubstitution.objects.filter(user=request.user, slot=slot)
            .order_by("-created_at")
            .first()
        )
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
