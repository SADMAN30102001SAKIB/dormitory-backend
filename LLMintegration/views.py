import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from .serializers import ChatRequestSerializer, ChatResponseSerializer
from django.conf import settings

@extend_schema(tags=["LLM Chatbot"])
class ChatbotView(APIView):
    permission_classes = [IsAuthenticated] # Only authenticated users can use the chatbot

    @extend_schema(
        request=ChatRequestSerializer,
        responses={
            200: ChatResponseSerializer,
            400: OpenApiResponse(description="Invalid request data"),
            401: OpenApiResponse(description="Authentication required"),
            500: OpenApiResponse(description="Internal server error"),
        },
        summary="Interact with the LLM Chatbot",
        description="Send a message to the LLM chatbot and get a response. "
                    "This endpoint provides academic and mental support based on a system prompt.",
    )
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_message = serializer.validated_data["message"]

        try:
            # Initialize the LangChain Google Generative AI model
            # The API key is automatically picked up from GOOGLE_API_KEY environment variable
            # or passed directly. We'll ensure it's passed from settings.
            llm = ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.7, # You can adjust temperature for creativity
            )
            
            # Define the system prompt
            system_prompt = SystemMessage(
                content=(
                    "You are an academic and mental support chatbot for students. "
                    "Provide helpful, empathetic, and concise advice. "
                    "For academic queries, offer guidance on study techniques, resources, or problem-solving approaches. "
                    "For mental support, offer encouraging words, suggest coping strategies, or recommend seeking professional help if appropriate. "
                    "Always maintain a supportive and non-judgmental tone."
                )
            )
            
            # Create the chat messages
            messages = [
                system_prompt,
                HumanMessage(content=user_message),
            ]
            
            # Invoke the LLM
            response = llm.invoke(messages)
            
            # Extract the content from the AI message
            llm_response_text = response.content

            response_serializer = ChatResponseSerializer({"response": llm_response_text})
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            # Log the error for debugging purposes
            print(f"Error interacting with LangChain/Gemini API: {e}")
            return Response(
                {"error": "Could not process your request. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

