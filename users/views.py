from django.contrib.auth.models import User
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Achievement,
    Course,
    Education,
    Follow,
    Institution,
    Interest,
    Project,
    Publication,
    Skill,
    WorkExperience,
    WorkOrganization,
)
from .serializers import (
    AchievementSerializer,
    CourseSerializer,
    EducationSerializer,
    FollowSerializer,
    InstitutionSerializer,
    InterestSerializer,
    LoginSerializer,
    ProfileSerializer,
    ProjectSerializer,
    PublicationSerializer,
    RegisterSerializer,
    SkillSerializer,
    UserBasicSerializer,
    UserSerializer,
    WorkExperienceSerializer,
    WorkOrganizationSerializer,
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


@extend_schema_view(
    get=extend_schema(
        summary="List Users",
        description="Get a list of all users with optional search by username or profile name",
        tags=["Users"],
        parameters=[
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="List users by username or profile name",
                required=False,
            )
        ],
    )
)
class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["username", "profile__name"]


@extend_schema(
    responses={
        200: UserSerializer,
        404: OpenApiResponse(description="User not found"),
    },
    summary="Get user by username",
    description="Retrieve a single user by their username",
    tags=["Users"],
)
class UserDetailView(RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = "username"  # Optional; default is 'pk'
    permission_classes = [permissions.AllowAny]


@extend_schema(
    responses={
        204: OpenApiResponse(description="User deleted successfully"),
        404: OpenApiResponse(description="User not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    summary="Delete User",
    description="Delete the current authenticated user's account. This action is irreversible.",
    tags=["Users"],
)
class UserDeleteView(generics.DestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(
    tags=["Profile"],
)
class ProfileUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile

    @extend_schema(
        summary="Retrieve User Profile",
        description="Fetch the authenticated user's profile information.",
        responses={
            200: ProfileSerializer,
            401: OpenApiResponse(description="Authentication required"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update User Profile",
        description="Fully update the authenticated user's profile. All required fields must be provided.",
        request=ProfileSerializer,
        responses={
            200: ProfileSerializer,
            400: OpenApiResponse(description="Validation errors"),
            401: OpenApiResponse(description="Authentication required"),
        },
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary="Partially Update User Profile",
        description="Partially update fields of the authenticated user's profile.",
        request=ProfileSerializer,
        responses={
            200: ProfileSerializer,
            400: OpenApiResponse(description="Validation errors"),
            401: OpenApiResponse(description="Authentication required"),
        },
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


# Profile-related ViewSets
@extend_schema_view(
    list=extend_schema(
        tags=["Institutions"],
        summary="List institutions",
        parameters=[
            OpenApiParameter(
                "search",
                description="Search institutions by name or location",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                "ordering",
                description="Order by name or location",
                required=False,
                type=str,
            ),
        ],
    ),
    create=extend_schema(
        tags=["Institutions"],
        summary="Create institution",
        description="Create a new institution",
    ),
    retrieve=extend_schema(
        tags=["Institutions"],
        summary="Get institution details",
        description="Retrieve details of a specific institution",
    ),
    update=extend_schema(
        tags=["Institutions"],
        summary="Update institution",
        description="Update an institution (full update)",
    ),
    partial_update=extend_schema(
        tags=["Institutions"],
        summary="Partially update institution",
        description="Partially update an institution",
    ),
    destroy=extend_schema(
        tags=["Institutions"],
        summary="Delete institution",
        responses={
            204: OpenApiResponse(description="Institution deleted successfully"),
            400: OpenApiResponse(description="Cannot delete institution in use"),
            404: OpenApiResponse(description="Institution not found"),
            401: OpenApiResponse(description="Authentication required"),
        },
        description="Delete an institution (only if not referenced by any education, project, or course)",
    ),
)
class InstitutionViewSet(viewsets.ModelViewSet):
    serializer_class = InstitutionSerializer
    permission_classes = [IsAuthenticated]
    queryset = Institution.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "location"]
    ordering_fields = ["name", "location"]
    ordering = ["name"]

    def destroy(self, request, *args, **kwargs):
        """Override destroy to prevent deletion if institution is in use"""
        instance = self.get_object()
        if (
            instance.educations.exists()
            or instance.projects.exists()
            or instance.courses.exists()
        ):
            return Response(
                {
                    "detail": "Cannot delete institution that is referenced by education records, projects, or courses."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


@extend_schema_view(
    list=extend_schema(
        tags=["Profile - Education"],
        summary="List user's education",
        responses={
            200: OpenApiResponse(description="List of education records"),
            401: OpenApiResponse(description="Authentication required"),
        },
        description="Get all education records for the authenticated user's profile",
    ),
    create=extend_schema(
        tags=["Profile - Education"],
        summary="Add new education",
        responses={
            201: OpenApiResponse(description="Education created successfully"),
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Authentication required"),
        },
        description="Add a new education record to the authenticated user's profile",
    ),
    retrieve=extend_schema(
        tags=["Profile - Education"],
        summary="Get education details",
        responses={
            200: OpenApiResponse(description="Education details"),
            404: OpenApiResponse(description="Education not found"),
            401: OpenApiResponse(description="Authentication required"),
        },
        description="Retrieve details of a specific education record",
    ),
    update=extend_schema(
        tags=["Profile - Education"],
        summary="Update education",
        responses={
            200: OpenApiResponse(description="Education updated successfully"),
            400: OpenApiResponse(description="Invalid data"),
            404: OpenApiResponse(description="Education not found"),
            401: OpenApiResponse(description="Authentication required"),
        },
        description="Update an education record (full update)",
    ),
    partial_update=extend_schema(
        tags=["Profile - Education"],
        summary="Partially update education",
        responses={
            200: OpenApiResponse(description="Education updated successfully"),
            400: OpenApiResponse(description="Invalid data"),
            404: OpenApiResponse(description="Education not found"),
            401: OpenApiResponse(description="Authentication required"),
        },
        description="Partially update an education record",
    ),
    destroy=extend_schema(
        tags=["Profile - Education"],
        summary="Delete education",
        responses={
            204: OpenApiResponse(description="Education deleted successfully"),
            404: OpenApiResponse(description="Education not found"),
            401: OpenApiResponse(description="Authentication required"),
        },
        description="Delete an education record from profile",
    ),
)
class EducationViewSet(viewsets.ModelViewSet):
    serializer_class = EducationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = []

    def get_queryset(self):
        return Education.objects.filter(profile=self.request.user.profile)

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user.profile)


@extend_schema_view(
    list=extend_schema(
        tags=["Profile - Skills"],
        summary="List user's skills",
        description="Get all skills associated with the authenticated user's profile",
    ),
    create=extend_schema(
        tags=["Profile - Skills"],
        summary="Add new skill",
        description="Add a new skill to the authenticated user's profile",
    ),
    retrieve=extend_schema(
        tags=["Profile - Skills"],
        summary="Get skill details",
        description="Retrieve details of a specific skill",
    ),
    update=extend_schema(
        tags=["Profile - Skills"],
        summary="Update skill",
        description="Update a skill (full update)",
    ),
    partial_update=extend_schema(
        tags=["Profile - Skills"],
        summary="Partially update skill",
        description="Partially update a skill",
    ),
    destroy=extend_schema(
        tags=["Profile - Skills"],
        summary="Delete skill",
        responses={
            204: OpenApiResponse(description="Skill deleted successfully"),
            404: OpenApiResponse(description="Skill not found"),
            401: OpenApiResponse(description="Authentication required"),
        },
        description="Delete a skill from profile",
    ),
)
class SkillViewSet(viewsets.ModelViewSet):
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = []  # No filtering needed for user's own skills

    def get_queryset(self):
        return self.request.user.profile.skills.all()

    def create(self, request, *args, **kwargs):
        # Get the skill name from request data
        skill_name = request.data.get("name")
        if not skill_name:
            return Response(
                {"name": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get or create the skill to avoid duplicates
        skill, created = Skill.objects.get_or_create(name=skill_name)

        # Add skill to user's profile if not already there
        if not self.request.user.profile.skills.filter(id=skill.id).exists():
            self.request.user.profile.skills.add(skill)

        # Return the skill data
        serializer = self.get_serializer(skill)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        skill = self.get_object()
        request.user.profile.skills.remove(skill)
        # Delete the skill itself if it's not used anywhere
        if not skill.profiles.exists():
            skill.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(
        tags=["Profile - Work Experience"],
        summary="List user's work experiences",
        description="Get all work experiences associated with the authenticated user's profile",
    ),
    create=extend_schema(
        tags=["Profile - Work Experience"],
        summary="Add new work experience",
        description="Add a new work experience to the authenticated user's profile",
    ),
    retrieve=extend_schema(
        tags=["Profile - Work Experience"],
        summary="Get work experience details",
        description="Retrieve details of a specific work experience",
    ),
    update=extend_schema(
        tags=["Profile - Work Experience"],
        summary="Update work experience",
        description="Update a work experience (full update)",
    ),
    partial_update=extend_schema(
        tags=["Profile - Work Experience"],
        summary="Partially update work experience",
        description="Partially update a work experience",
    ),
    destroy=extend_schema(
        tags=["Profile - Work Experience"],
        summary="Delete work experience",
        responses={
            204: OpenApiResponse(description="Work experience deleted successfully"),
            404: OpenApiResponse(description="Work experience not found"),
            401: OpenApiResponse(description="Authentication required"),
        },
        description="Delete a work experience from profile",
    ),
)
class WorkExperienceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkExperienceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = []  # No filtering needed for user's own work experiences

    def get_queryset(self):
        return WorkExperience.objects.filter(profile=self.request.user.profile)

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user.profile)


@extend_schema_view(
    list=extend_schema(
        tags=["Profile - Projects"],
        summary="List user's projects",
        description="Get all projects associated with the authenticated user's profile",
    ),
    create=extend_schema(
        tags=["Profile - Projects"],
        summary="Add new project",
        description="Add a new project to the authenticated user's profile",
    ),
    retrieve=extend_schema(
        tags=["Profile - Projects"],
        summary="Get project details",
        description="Retrieve details of a specific project",
    ),
    update=extend_schema(
        tags=["Profile - Projects"],
        summary="Update project",
        description="Update a project (full update)",
    ),
    partial_update=extend_schema(
        tags=["Profile - Projects"],
        summary="Partially update project",
        description="Partially update a project",
    ),
    destroy=extend_schema(
        tags=["Profile - Projects"],
        summary="Delete project",
        responses={
            204: OpenApiResponse(description="Project deleted successfully"),
            404: OpenApiResponse(description="Project not found"),
            401: OpenApiResponse(description="Authentication required"),
        },
        description="Delete a project from profile",
    ),
)
class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = []  # No filtering needed for user's own projects

    def get_queryset(self):
        return Project.objects.filter(profile=self.request.user.profile)

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user.profile)


@extend_schema_view(
    list=extend_schema(
        tags=["Profile - Achievements"],
        summary="List user's achievements",
        description="Get all achievements associated with the authenticated user's profile",
    ),
    create=extend_schema(
        tags=["Profile - Achievements"],
        summary="Add new achievement",
        description="Add a new achievement to the authenticated user's profile",
    ),
    retrieve=extend_schema(
        tags=["Profile - Achievements"],
        summary="Get achievement details",
        description="Retrieve details of a specific achievement",
    ),
    update=extend_schema(
        tags=["Profile - Achievements"],
        summary="Update achievement",
        description="Update an achievement (full update)",
    ),
    partial_update=extend_schema(
        tags=["Profile - Achievements"],
        summary="Partially update achievement",
        description="Partially update an achievement",
    ),
    destroy=extend_schema(
        tags=["Profile - Achievements"],
        summary="Delete achievement",
        responses={
            204: OpenApiResponse(description="Achievement deleted successfully"),
            404: OpenApiResponse(description="Achievement not found"),
            401: OpenApiResponse(description="Authentication required"),
        },
        description="Delete an achievement from profile",
    ),
)
class AchievementViewSet(viewsets.ModelViewSet):
    serializer_class = AchievementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = []  # No filtering needed for user's own achievements

    def get_queryset(self):
        return Achievement.objects.filter(profile=self.request.user.profile)

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user.profile)


@extend_schema_view(
    list=extend_schema(
        tags=["Profile - Courses"],
        summary="List user's courses",
        description="Get all courses associated with the authenticated user's profile",
    ),
    create=extend_schema(
        tags=["Profile - Courses"],
        summary="Add new course",
        description="Add a new course to the authenticated user's profile",
    ),
    retrieve=extend_schema(
        tags=["Profile - Courses"],
        summary="Get course details",
        description="Retrieve details of a specific course",
    ),
    update=extend_schema(
        tags=["Profile - Courses"],
        summary="Update course",
        description="Update a course (full update)",
    ),
    partial_update=extend_schema(
        tags=["Profile - Courses"],
        summary="Partially update course",
        description="Partially update a course",
    ),
    destroy=extend_schema(
        tags=["Profile - Courses"],
        summary="Delete course",
        responses={
            204: OpenApiResponse(description="Course deleted successfully"),
            404: OpenApiResponse(description="Course not found"),
            401: OpenApiResponse(description="Authentication required"),
        },
        description="Delete a course from profile",
    ),
)
class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = []  # No filtering needed for user's own courses

    def get_queryset(self):
        return Course.objects.filter(profile=self.request.user.profile)

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user.profile)


@extend_schema_view(
    list=extend_schema(
        tags=["Profile - Interests"],
        summary="List user's interests",
        description="Get all interests associated with the authenticated user's profile",
    ),
    create=extend_schema(
        tags=["Profile - Interests"],
        summary="Add new interest",
        description="Add a new interest to the authenticated user's profile",
    ),
    retrieve=extend_schema(
        tags=["Profile - Interests"],
        summary="Get interest details",
        description="Retrieve details of a specific interest",
    ),
    update=extend_schema(
        tags=["Profile - Interests"],
        summary="Update interest",
        description="Update an interest (full update)",
    ),
    partial_update=extend_schema(
        tags=["Profile - Interests"],
        summary="Partially update interest",
        description="Partially update an interest",
    ),
    destroy=extend_schema(
        tags=["Profile - Interests"],
        summary="Delete interest",
        responses={
            204: OpenApiResponse(description="Interest deleted successfully"),
            404: OpenApiResponse(description="Interest not found"),
            401: OpenApiResponse(description="Authentication required"),
        },
        description="Delete an interest from profile",
    ),
)
class InterestViewSet(viewsets.ModelViewSet):
    serializer_class = InterestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = []  # No filtering needed for user's own interests

    def get_queryset(self):
        return self.request.user.profile.interests.all()

    def create(self, request, *args, **kwargs):
        # Get the interest name from request data
        interest_name = request.data.get("name")
        if not interest_name:
            return Response(
                {"name": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get or create the interest to avoid duplicates
        interest, created = Interest.objects.get_or_create(name=interest_name)

        # Add interest to user's profile if not already there
        if not self.request.user.profile.interests.filter(id=interest.id).exists():
            self.request.user.profile.interests.add(interest)

        # Return the interest data
        serializer = self.get_serializer(interest)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        interest = self.get_object()
        request.user.profile.interests.remove(interest)
        # Delete the interest itself if it's not used anywhere
        if not interest.profiles.exists():
            interest.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(
        tags=["Profile - Publications"],
        summary="List publications",
        description="Get all publications for the authenticated user's profile",
    ),
    create=extend_schema(
        tags=["Profile - Publications"],
        summary="Create publication",
        description="Add a new publication to profile",
    ),
    retrieve=extend_schema(
        tags=["Profile - Publications"],
        summary="Get publication details",
        description="Get details of a specific publication",
    ),
    update=extend_schema(
        tags=["Profile - Publications"],
        summary="Update publication",
        description="Update an existing publication",
    ),
    partial_update=extend_schema(
        tags=["Profile - Publications"],
        summary="Partially update publication",
        description="Partially update an existing publication",
    ),
    destroy=extend_schema(
        tags=["Profile - Publications"],
        summary="Delete publication",
        responses={
            204: OpenApiResponse(description="Publication deleted successfully"),
            404: OpenApiResponse(description="Publication not found"),
            401: OpenApiResponse(description="Authentication required"),
        },
        description="Delete a publication from profile",
    ),
)
class PublicationViewSet(viewsets.ModelViewSet):
    serializer_class = PublicationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = []  # No filtering needed for user's own publications

    def get_queryset(self):
        return Publication.objects.filter(profile=self.request.user.profile)

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user.profile)


@extend_schema_view(
    list=extend_schema(
        tags=["Organizations"],
        summary="List organizations",
        parameters=[
            OpenApiParameter(
                "search",
                description="Search organizations by name or location",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                "ordering",
                description="Order by name or location",
                required=False,
                type=str,
            ),
        ],
    ),
    create=extend_schema(
        tags=["Organizations"],
        summary="Create organization",
        description="Create a new organization",
    ),
    retrieve=extend_schema(
        tags=["Organizations"],
        summary="Get organization details",
        description="Retrieve details of a specific organization",
    ),
    update=extend_schema(
        tags=["Organizations"],
        summary="Update organization",
        description="Update an organization (full update)",
    ),
    partial_update=extend_schema(
        tags=["Organizations"],
        summary="Partially update organization",
        description="Partially update an organization",
    ),
    destroy=extend_schema(
        tags=["Organizations"],
        summary="Delete organization",
        responses={
            204: OpenApiResponse(description="Organization deleted successfully"),
            400: OpenApiResponse(description="Cannot delete organization in use"),
            404: OpenApiResponse(description="Organization not found"),
            401: OpenApiResponse(description="Authentication required"),
        },
        description="Delete an organization (only if not referenced by any work experience)",
    ),
)
class WorkOrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = WorkOrganizationSerializer
    permission_classes = [IsAuthenticated]
    queryset = WorkOrganization.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "location"]
    ordering_fields = ["name", "location"]
    ordering = ["name"]

    def destroy(self, request, *args, **kwargs):
        """Override destroy to prevent deletion if organization is in use"""
        instance = self.get_object()
        if instance.work_experiences.exists():
            return Response(
                {
                    "detail": "Cannot delete organization that is referenced by work experiences."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


# Follow-related views
class FollowUserView(APIView):
    """Follow a user"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Profile - Follow"],
        request=None,
        summary="Follow user",
        responses={
            201: OpenApiResponse(description="Successfully followed user"),
            400: OpenApiResponse(
                description="Bad request (already following, self-follow, etc.)"
            ),
            404: OpenApiResponse(description="User not found"),
        },
        description="Follow a user by username",
    )
    def post(self, request, username):
        try:
            user_to_follow = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if trying to follow self
        if request.user == user_to_follow:
            return Response(
                {"detail": "You cannot follow yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if already following
        follow_exists = Follow.objects.filter(
            follower=request.user, following=user_to_follow
        ).exists()

        if follow_exists:
            return Response(
                {"detail": "You are already following this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create follow relationship
        follow = Follow.objects.create(follower=request.user, following=user_to_follow)
        serializer = FollowSerializer(follow)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UnfollowUserView(APIView):
    """Unfollow a user"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Profile - Follow"],
        summary="Unfollow user",
        request=None,
        responses={
            204: OpenApiResponse(description="Successfully unfollowed user"),
            404: OpenApiResponse(description="User not found or not following"),
        },
        description="Unfollow a user by username",
    )
    def delete(self, request, username):
        try:
            user_to_unfollow = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Find and delete follow relationship
        try:
            follow = Follow.objects.get(
                follower=request.user, following=user_to_unfollow
            )
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Follow.DoesNotExist:
            return Response(
                {"detail": "You are not following this user."},
                status=status.HTTP_404_NOT_FOUND,
            )


@extend_schema(
    tags=["Profile - Follow"],
    responses={
        200: UserBasicSerializer(many=True),
        404: OpenApiResponse(description="User not found"),
    },
    description="Get list of users who follow the specified user",
    summary="Get user followers",
)
class UserFollowersView(generics.ListAPIView):
    """Get list of followers for a user"""

    serializer_class = UserBasicSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = []

    def get_queryset(self):
        username = self.kwargs.get("username")
        try:
            user = User.objects.get(username=username)
            # Get follower IDs and return a proper QuerySet
            follower_ids = Follow.objects.filter(following=user).values_list(
                "follower_id", flat=True
            )
            return User.objects.filter(id__in=follower_ids).select_related("profile")
        except User.DoesNotExist:
            return User.objects.none()


@extend_schema(
    tags=["Profile - Follow"],
    responses={
        200: UserBasicSerializer(many=True),
        404: OpenApiResponse(description="User not found"),
    },
    description="Get list of users that the specified user is following",
    summary="Get user following",
)
class UserFollowingView(generics.ListAPIView):
    """Get list of users that a user is following"""

    serializer_class = UserBasicSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = []

    def get_queryset(self):
        username = self.kwargs.get("username")
        try:
            user = User.objects.get(username=username)
            # Get following IDs and return a proper QuerySet
            following_ids = Follow.objects.filter(follower=user).values_list(
                "following_id", flat=True
            )
            return User.objects.filter(id__in=following_ids).select_related("profile")
        except User.DoesNotExist:
            return User.objects.none()


class FollowStatusView(APIView):
    """Check if current user is following another user"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Profile - Follow"],
        summary="Check follow status",
        responses={
            200: OpenApiResponse(description="Follow status information"),
            404: OpenApiResponse(description="User not found"),
        },
        description="Check follow status between current user and specified user",
    )
    def get(self, request, username):
        try:
            target_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if request.user == target_user:
            return Response(
                {
                    "is_following": None,
                    "follows_you": None,
                    "message": "Cannot check follow status with yourself",
                }
            )

        is_following = Follow.objects.filter(
            follower=request.user, following=target_user
        ).exists()

        follows_you = Follow.objects.filter(
            follower=target_user, following=request.user
        ).exists()

        return Response(
            {
                "is_following": is_following,
                "follows_you": follows_you,
                "mutual": is_following and follows_you,
            }
        )
