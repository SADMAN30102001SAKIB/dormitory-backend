from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .chat_utils import generate_bot_response
from .models import Conversation
from .serializers import *


@extend_schema_view(
    list=extend_schema(
        tags=["LLM"],
        description="Get a list of all conversations created by the authenticated user.",
        summary="List all conversations",
    ),
    retrieve=extend_schema(
        tags=["LLM"],
        description="Retrieve details of a single conversation by its ID.",
        summary="Get conversation details",
    ),
    create=extend_schema(
        tags=["LLM"],
        description="Create a new conversation for the authenticated user. Once created, get the ID from the response to POST /api/llm/conversations/{id}/send.",
        summary="Create a new conversation",
    ),
    update=extend_schema(
        tags=["LLM"],
        description="Replace an entire conversation object by its ID.",
        summary="Update a conversation's title",
    ),
    partial_update=extend_schema(
        tags=["LLM"],
        description="Update specific fields of a conversation (e.g., title) without replacing the entire object.",
        summary="Partially update a conversation's title",
    ),
    destroy=extend_schema(
        tags=["LLM"],
        description="Delete a conversation by its ID. This action is irreversible and removes the conversation and its message history.",
        responses={
            204: OpenApiResponse(description="Conversation deleted successfully"),
            401: OpenApiResponse(description="Authentication required"),
        },
        summary="Delete a conversation",
    ),
    send_message=extend_schema(
        tags=["LLM"],
        description="Send a message to the bot and get a response. Needs a valid conversation ID in the URL. Use POST /api/llm/conversations to create a conversation first, then use the returned ID here.",
        responses={
            200: OpenApiResponse(
                description="Successful response from bot",
                response={
                    "type": "object",
                    "properties": {
                        "reply": {"type": "string"},
                        "conversation": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "title": {"type": "string"},
                                "summary": {"type": "string"},
                                "created_at": {"type": "string", "format": "date-time"},
                                "updated_at": {"type": "string", "format": "date-time"},
                                "messages": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "sender": {"type": "string"},
                                            "text": {"type": "string"},
                                            "timestamp": {
                                                "type": "string",
                                                "format": "date-time",
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            ),
            400: OpenApiResponse(description="Bad request"),
        },
        summary="Send a message to the bot",
    ),
)
class ConversationViewSet(
    viewsets.ModelViewSet
):  # ModelViewSet CRUD under the hood flow https://chatgpt.com/share/683cad23-cdc4-8010-b82f-6e067ea30249
    # queryset = Conversation.objects.all() #default queryset for ModelViewSet. But as we have overridden get_queryset, this is no longer needed.
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["title", "summary"]
    ordering_fields = ["updated_at", "created_at"]

    def get_queryset(self):  # overriden
        if getattr(
            self, "swagger_fake_view", False
        ):  # checks if self.swagger_fake_view is true. if yes, get_queryset returns no objects as shortcircuit. if no, then the default value - false is evaluated, and this if check is passed.
            return Conversation.objects.none()
        user = self.request.user
        if not user or not user.is_authenticated:
            return Conversation.objects.none()
        return Conversation.objects.filter(user=user).order_by("-updated_at")

    def perform_create(self, serializer):  # overriden
        serializer.save(
            user=self.request.user
        )  # POST request calles .create() which returns json representation of the created instance.

    @action(
        detail=True,
        methods=["POST"],
        url_path="send",
        serializer_class=SendMessageSerializer,
    )  # action decorator creates a custom action on the viewset. detail=True means this action is for a single object (conversation). methods=["POST"] means it will respond to POST requests. url_path="send" sets the URL path for this action. serializer_class=SendMessageSerializer specifies which serializer to use for this action.
    # Because detail=True, DRF expects the URL to include a primary key (or lookup field) to identify the specific resource. When you use a ModelViewSet, DRF automatically generates URL patterns for standard actions (e.g., GET /api/conversations/, POST /api/conversations/, GET /api/conversations/{id}/, etc.). For custom actions like send_message, the @action decorator extends this. With detail=True, DRF appends the action's url_path to the detail route, resulting in POST /api/conversations/{id}/send/
    def send_message(
        self, request, pk=None
    ):  # thus pk is populated by DRF from the URL.
        """
        POST /api/conversations/{id}/send/
        Body: { "message": "…user's message…" }
        """
        serializer = self.get_serializer(
            data=request.data
        )  # returns an instance of SendMessageSerializer. self.get_serializer returns the serializer class specified in the action decorator (serializer_class=SendMessageSerializer). then we are passing the request data to it for validation.
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_text = serializer.validated_data[
            "message"
        ].strip()  # DRF parses the incoming JSON ({ "message": "…" }) into validated_data = {"message": "...user input..."}.
        conv = self.get_object()  # conversation object for the pk

        # Use updated generate_bot_response which returns a dict with 'reply' and 'conversation'
        result = generate_bot_response(
            conv, user_text
        )  # result is already a dict with 'reply' and 'conversation' keys, so we can directly return it instead of serializing it like before.
        return Response(result, status=status.HTTP_200_OK)

        ## # Old code for reference, but not used anymore
        #     bot_reply = generate_bot_response(
        #     conv, user_text
        # )  # inside generate_bot_response, the user_text will be appended to the conversation, and the bot's reply will be generated and saved as history and the conversation summary will be  updated.
        # # Return “reply” plus the updated Conversation (with all messages & new summary)
        # convo_data = ConversationSerializer(
        #     conv, context={"request": request}
        # ).data  # serializes the updated conversation object as JSON to send to client (.data)
        # return Response(
        #     {"reply": bot_reply, "conversation": convo_data},
        #     status=status.HTTP_200_OK,
        # )
