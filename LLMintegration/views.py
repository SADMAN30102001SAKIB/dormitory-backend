from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Conversation, Message
from .serializers import *
from .chat_utils import generate_bot_response
from drf_spectacular.utils import extend_schema_view, extend_schema

@extend_schema_view(
    list=extend_schema(tags=["LLM"]),
    retrieve=extend_schema(tags=["LLM"]),
    create=extend_schema(tags=["LLM"], description="Use this for creating a new conversation. Once created, extract the conversation ID from the response to use in subsequent requests to POST api/llm/conversations/{id}/send/."),
    update=extend_schema(tags=["LLM"]),
    partial_update=extend_schema(tags=["LLM"]),
    destroy=extend_schema(tags=["LLM"]),
    send_message=extend_schema(tags=["LLM"], description="Send a message to the bot and get a response. Needs a valid conversation ID in the URL. Use POST /api/llm/conversations/ to create a conversation first, then use the returned ID here.")
)
class ConversationViewSet(viewsets.ModelViewSet): #ModelViewSet CRUD under the hood flow https://chatgpt.com/share/683cad23-cdc4-8010-b82f-6e067ea30249
    #queryset = Conversation.objects.all() #default queryset for ModelViewSet. But as we have overridden get_queryset, this is no longer needed.
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self): #overriden
        if getattr(self, "swagger_fake_view", False): #checks if self.swagger_fake_view is true. if yes, get_queryset returns no objects as shortcircuit. if no, then the default value - false is evaluated, and this if check is passed.
            return Conversation.objects.none()
        user = self.request.user
        if not user or not user.is_authenticated:
            return Conversation.objects.none()
        return Conversation.objects.filter(user=user).order_by("-updated_at")

    def perform_create(self, serializer): #overriden
        serializer.save(user=self.request.user) # POST request calles .create() which returns json representation of the created instance. 

    @action(detail=True, methods=["POST"], url_path="send", serializer_class=SendMessageSerializer) #action decorator creates a custom action on the viewset. detail=True means this action is for a single object (conversation). methods=["POST"] means it will respond to POST requests. url_path="send" sets the URL path for this action. serializer_class=SendMessageSerializer specifies which serializer to use for this action.
    #Because detail=True, DRF expects the URL to include a primary key (or lookup field) to identify the specific resource. When you use a ModelViewSet, DRF automatically generates URL patterns for standard actions (e.g., GET /api/conversations/, POST /api/conversations/, GET /api/conversations/{id}/, etc.). For custom actions like send_message, the @action decorator extends this. With detail=True, DRF appends the action’s url_path to the detail route, resulting in POST /api/conversations/{id}/send/
    def send_message(self, request, pk=None): # thus pk is populated by DRF from the URL.
        """
        POST /api/conversations/{id}/send/
        Body: { "message": "…user’s message…" }
        """
        serializer = self.get_serializer(data=request.data)  #returns an instance of SendMessageSerializer. self.get_serializer returns the serializer class specified in the action decorator (serializer_class=SendMessageSerializer). then we are passing the request data to it for validation.
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_text = serializer.validated_data["message"].strip() #DRF parses the incoming JSON ({ "message": "…" }) into validated_data = {"message": "...user input..."}.
        conv = self.get_object() #conversation object for the pk

        bot_reply = generate_bot_response(conv, user_text) #inside generate_bot_response, the user_text will be appended to the conversation, and the bot's reply will be generated and saved as history and the conversation summary will be  updated.
        
        # Return “reply” plus the updated Conversation (with all messages & new summary)
        convo_data = ConversationSerializer(conv, context={"request": request}).data  #serializes the updated conversation object as JSON to send to client (.data)
        return Response(
            {"reply": bot_reply, "conversation": convo_data},
            status=status.HTTP_200_OK,
        )
