from rest_framework import serializers
from .models import Domain, TrackedTime


class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = "__all__"
        read_only_fields = [
            "user"
        ]  # Ensure the user field is NOT required to send via JSON manually on creation, rather viewsets will set the authenticated user automatically


class TrackedTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackedTime
        fields = "__all__"
        read_only_fields = ["user"]


class TimerStartSerializer(serializers.Serializer):
    domain = serializers.IntegerField(
        required=False, help_text="ID of the domain to track time for."
    )
    goal = serializers.CharField(
        required=False, help_text="The goal for this study session."
    )


class LiveUsersSerializers(serializers.Serializer):
    user = serializers.CharField()
    domain = serializers.CharField()
    goal = serializers.CharField()
    total_studied_time_today = serializers.DurationField()
    read_only_fields = ["user"]


class EndTimerSerializer(
    serializers.Serializer
):  #  a custom serializer specifically for the end_timer action that does not require any fields. This will ensure that the Swagger UI reflects the correct schema for the endpoint.
    pass


# Add serializer for active timer status
class ActiveTimerStatusSerializer(serializers.Serializer):
    active = serializers.BooleanField()
    elapsed_time = serializers.DurationField(allow_null=True)
    goal = serializers.CharField(allow_null=True, required=False)
