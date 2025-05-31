from django.contrib.auth.models import User
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import filters, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    LoginSerializer,
    ProfileSerializer,
    RegisterSerializer,
    UserSerializer,
)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                description="Login successful",
                response={
                    "type": "object",
                    "properties": {
                        "tokens": {
                            "type": "object",
                            "properties": {
                                "refresh": {"type": "string"},
                                "access": {"type": "string"},
                            },
                        },
                        "user": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "username": {"type": "string"},
                                "email": {"type": "string"},
                            },
                        },
                    },
                },
            ),
            400: OpenApiResponse(description="Invalid credentials"),
        },
        summary="User Login",
        description="Login with email and password to receive JWT tokens",
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            tokens = serializer.get_tokens(user)

            return Response(
                {
                    "tokens": tokens,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                    },
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=RegisterSerializer,
    responses={
        201: UserSerializer,
        400: OpenApiResponse(description="Validation errors"),
    },
    summary="User Registration",
    description="Register a new user with username, email, password, and name",
    tags=["Authentication"],
)
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer


@extend_schema(
    responses={200: UserSerializer(many=True)},
    parameters=[
        {
            "name": "search",
            "description": "Search users by username",
            "required": False,
            "type": "string",
            "in": "query",
        }
    ],
    summary="List Users",
    description="Get a list of all users with optional search by username",
    tags=["Users"],
)
class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["username"]


@extend_schema(
    request=ProfileSerializer,
    responses={
        200: ProfileSerializer,
        401: OpenApiResponse(description="Authentication required"),
        400: OpenApiResponse(description="Validation errors"),
    },
    summary="Get/Update User Profile",
    description="Retrieve or update the authenticated user's profile information",
    tags=["Profile"],
)
class ProfileUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile
