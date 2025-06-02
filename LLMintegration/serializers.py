from rest_framework import serializers

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "sender", "text", "timestamp"]


class ConversationSerializer(serializers.ModelSerializer):
    # Nested serializer for messages. this is not a field in the model, but a representation of the related messages.
    messages = MessageSerializer(many=True, read_only=True)
    #  Swagger will reflect the serializer's requirements, not the model's. serializer inherits the model field’s settings (required or not) unless you override them here.
    title = serializers.CharField(
        max_length=255, required=False, allow_blank=True, allow_null=True
    )

    class Meta:
        model = Conversation
        fields = ["id", "title", "summary", "created_at", "updated_at", "messages"]
        read_only_fields = [
            "summary",
            "created_at",
            "updated_at",
            "messages",
        ]  # These fields are read-only and cannot be modified through the API. DRF's ModelSerializer will auto-treat any auto-generated primary key (like id) as read-only.
        """
        Read-only in DRF serializers simply means:
        • You'll see the field in the output (serializer.data) but the serializer will ignore it on input.  
        • You cannot pass it in your POST/PATCH payload—any value you send for a read-only field is dropped. (you can edit title, but not summary, created_at, updated_at, messages. Note messages here is a nested serializer not the raw message text. you cannot send a list of messages to create or update the conversation.)     
        • It doesn't stop Django from creating the model instance; it just means you don't set those fields via the API.  
        """


class SendMessageSerializer(serializers.Serializer):
    message = serializers.CharField(
        max_length=2000, help_text="The user's chat text to send to the bot"
    )
