from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AchievementViewSet,
    CourseViewSet,
    EducationViewSet,
    InstitutionViewSet,
    InterestViewSet,
    LoginView,
    ProfileUpdateView,
    ProjectViewSet,
    PublicationViewSet,
    RegisterView,
    SkillViewSet,
    UserDeleteView,
    UserDetailView,
    UserListView,
    WorkExperienceViewSet,
    WorkOrganizationViewSet,
)

# Create router for ViewSets
router = DefaultRouter(trailing_slash=False)
router.register("institutions", InstitutionViewSet, basename="institutions")
router.register("organizations", WorkOrganizationViewSet, basename="organizations")
router.register("profile/education", EducationViewSet, basename="profile-education")
router.register("profile/skills", SkillViewSet, basename="profile-skills")
router.register(
    "profile/work-experiences",
    WorkExperienceViewSet,
    basename="profile-work-experiences",
)
router.register("profile/projects", ProjectViewSet, basename="profile-projects")
router.register(
    "profile/achievements", AchievementViewSet, basename="profile-achievements"
)
router.register(
    "profile/publications", PublicationViewSet, basename="profile-publications"
)
router.register("profile/courses", CourseViewSet, basename="profile-courses")
router.register("profile/interests", InterestViewSet, basename="profile-interests")

urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    path("login", LoginView.as_view(), name="login"),
    path("users", UserListView.as_view(), name="user-list"),
    path("profile", ProfileUpdateView.as_view(), name="profile"),
    path("user/<str:username>", UserDetailView.as_view(), name="user-detail"),
    path("user", UserDeleteView.as_view(), name="user-delete"),
    path("", include(router.urls)),
]
