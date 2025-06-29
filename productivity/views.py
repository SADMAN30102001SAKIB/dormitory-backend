from drf_spectacular.utils import extend_schema
from django.utils import timezone
from datetime import datetime, time, timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Q
from .models import Domain, TrackedTime
from .serializers import (
    DomainSerializer,
    TrackedTimeSerializer,
    LiveUsersSerializers,
    TimerStartSerializer,
    EndTimerSerializer,
    ActiveTimerStatusSerializer,  # added for active timer status view
)


@extend_schema(tags=["Productivity - Domain (aka Courses) Management"])
class DomainViewSet(viewsets.ModelViewSet):
    serializer_class = DomainSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Domain.objects.none()
        return Domain.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema(tags=["Productivity - Tracked Sessions Management"])
class TrackedTimeViewSet(viewsets.ModelViewSet):
    serializer_class = TrackedTimeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return TrackedTime.objects.none()
        return TrackedTime.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        tags=["Productivity - Timer Operations"],
        request=TimerStartSerializer,
        responses={201: TrackedTimeSerializer},
        summary="Start a new study timer",
        description="Starts a new timer for a specific domain (i.e. can be a course like CSE 3103, project, prep etc. Domain is used to group the goals.) and goal (session description like CFG CT Prep). Both are optional. The Domain field is an INTEGER field that refers to the ID of the domain to track time for. To create a domain, refer to PRODUCTIVY - DOMAIN MANAGEMENT section. The goal field is a CHAR field that describes the goal for this study session.",
    )
    @action(detail=False, methods=["post"], url_path="start-timer")
    def start_timer(self, request):
        serializer = TimerStartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        domain_id = serializer.validated_data.get("domain")
        goal = serializer.validated_data.get("goal")

        active_timer = TrackedTime.objects.filter(
            user=request.user, end_time__isnull=True
        ).exists()
        if active_timer:
            return Response(
                {"error": "An active timer already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        domain = None
        if domain_id:
            try:
                domain = Domain.objects.get(id=domain_id, user=request.user)
            except Domain.DoesNotExist:
                return Response(
                    {"error": "Domain not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        tracked_time = TrackedTime.objects.create(
            user=request.user, domain=domain, goal=goal, start_time=timezone.now()
        )
        serializer = self.get_serializer(tracked_time)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Productivity - Timer Operations"],
        request=EndTimerSerializer,  # Use the new serializer
        responses={200: TrackedTimeSerializer},
        summary="End the current study timer",
        description="Ends the currently active study timer for the user.",
    )
    @action(detail=False, methods=["post"], url_path="end-timer")
    def end_timer(self, request):
        try:
            active_timer = TrackedTime.objects.get(
                user=request.user, end_time__isnull=True
            )
        except TrackedTime.DoesNotExist:
            return Response(
                {"error": "No active timer found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        active_timer.end_time = timezone.now()
        active_timer.save()
        serializer = self.get_serializer(active_timer)
        return Response(serializer.data)

    @extend_schema(
        tags=["Productivity - Timer Operations"],
        responses={200: ActiveTimerStatusSerializer},
        summary="Get active timer status",
        description="Returns whether the authenticated user has an active timer and the elapsed time if active.",
    )
    @action(detail=False, methods=["get"], url_path="active-timer-status")
    def active_timer_status(self, request):
        # Check for an active timer for the user
        active_timer = TrackedTime.objects.filter(
            user=request.user, end_time__isnull=True
        ).first()
        if active_timer:
            elapsed_time = timezone.now() - active_timer.start_time
            data = {"active": True, "elapsed_time": elapsed_time}
        else:
            data = {"active": False, "elapsed_time": None}
        serializer = ActiveTimerStatusSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Productivity - Timer Operations"])
class LiveUsersView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Productivity - Timer Operations"],
        responses={200: LiveUsersSerializers(many=True)},
        summary="List actively studying users",
        description="Returns a list of users who are currently studying, along with their domain, goal, and total study time for the day.",
    )
    def get(self, request):
        # Get today's date to filter timers
        today = timezone.now().date()

        # Query active timers (timers without an end time) and prefetch related domain, goal, and user data
        active_timers = TrackedTime.objects.filter(
            end_time__isnull=True
        ).select_related("domain", "user")

        # Extract user IDs from active timers
        user_ids = [timer.user.id for timer in active_timers]

        # Query finished timers for today and calculate total duration for each user
        # This query filters timers that have an end time (i.e., completed timers) and started today.
        # It groups the results by user_id and calculates the total duration of all completed timers for each user.
        finished_today = (
            TrackedTime.objects.filter(
                user_id__in=user_ids,  # Only include users who have active timers
                end_time__isnull=False,  # Ensure the timer has an end time (completed)
                start_time__date=today,  # Ensure the timer started today
            )
            .values("user_id")  # Group by user_id
            .annotate(
                total_duration=Sum("duration")
            )  # Calculate the total duration for each user
        )

        # Create a mapping of user IDs to their total duration for finished timers
        # This dictionary allows quick lookup of the total duration for each user.
        finished_today_map = {
            item["user_id"]: item["total_duration"] for item in finished_today
        }

        # Prepare response data by combining active timers and finished durations
        # This loop iterates over all users' active timers and combines their duration with their finished durations.
        response_data = []
        for timer in active_timers:
            user = timer.user  # Get the user associated with the active timer
            # Retrieve the total duration for the user from finished_today_map, defaulting to 0 if not found
            total_duration_today = finished_today_map.get(user.id, timedelta(0))

            # Add the duration of the active timer (from its start time to now) to the total duration
            total_duration_today += timezone.now() - timer.start_time

            # Append user details and study session information to the response
            response_data.append(
                {
                    "user": user.username,  # Username of the user
                    "domain": (
                        timer.domain.name if timer.domain else None
                    ),  # Domain name or None if not set
                    "goal": (
                        timer.goal if timer.goal else None
                    ),  # Goal description or None if not set
                    "total_studied_time_today": total_duration_today,  # Total study time for today
                }
            )

        # Serialize the response data and return it
        serializer = LiveUsersSerializers(response_data, many=True)
        return Response(serializer.data)
