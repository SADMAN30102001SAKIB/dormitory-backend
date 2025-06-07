from django.contrib import admin
from django.contrib.auth.models import Permission

from .models import (
    Achievement,
    Course,
    Education,
    Follow,
    Institution,
    Interest,
    Profile,
    Project,
    Publication,
    Skill,
    WorkExperience,
    WorkOrganization,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "name", "gender", "personal_website"]
    list_filter = ["gender"]
    search_fields = ["user__username", "name"]
    filter_horizontal = ("skills", "interests")


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ["name", "location", "website"]
    search_fields = ["name", "location"]


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = [
        "major",
        "degree",
        "institution",
        "profile",
        "start_date",
        "end_date",
        "is_current",
    ]
    list_filter = ["degree", "is_current", "start_date"]
    search_fields = [
        "major",
        "institution__name",
        "profile__user__username",
        "profile__name",
    ]
    autocomplete_fields = ["institution"]


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(WorkOrganization)
class WorkOrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "location", "website"]
    search_fields = ["name", "location"]


@admin.register(WorkExperience)
class WorkExperienceAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "organization",
        "profile",
        "experience_type",
        "start_date",
        "is_current",
    ]
    list_filter = ["experience_type", "is_current", "start_date"]
    search_fields = ["title", "organization__name", "profile__user__username"]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "profile", "project_type", "start_date", "is_ongoing"]
    list_filter = ["project_type", "is_ongoing", "start_date"]
    search_fields = ["title", "description", "profile__user__username"]


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ["title", "profile", "achievement_type", "issuer", "date_received"]
    list_filter = ["achievement_type", "date_received"]
    search_fields = ["title", "issuer", "profile__user__username"]


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "profile",
        "publication_type",
        "authors",
        "publication_date",
    ]
    list_filter = ["publication_type", "publication_date"]
    search_fields = ["title", "authors", "profile__user__username"]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["title", "provider", "profile", "completion_date"]
    list_filter = ["completion_date"]
    search_fields = ["title", "provider", "profile__user__username"]


@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ["follower", "following", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["follower__username", "following__username"]
    raw_id_fields = ["follower", "following"]
    readonly_fields = ["created_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("follower", "following")


admin.site.register(Permission)
