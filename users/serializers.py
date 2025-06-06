from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Achievement,
    Course,
    Education,
    Institution,
    Interest,
    Profile,
    Project,
    Publication,
    Skill,
    WorkExperience,
    WorkOrganization,
)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise serializers.ValidationError("User doesn't exist.")

            user = authenticate(username=user.username, password=password)

            if not user:
                raise serializers.ValidationError("Invalid email or password.")

            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")

            attrs["user"] = user
            return attrs
        else:
            raise serializers.ValidationError("Must provide email and password.")

    def get_tokens(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }


class RegisterSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "name"]
        read_only_fields = ["id"]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already registered.")
        return value

    def create(self, validated_data):
        name = validated_data.pop("name")
        user = User.objects.create_user(**validated_data)
        user.profile.name = name
        user.profile.save()
        return user


# Related model serializers
class InstitutionSerializer(serializers.ModelSerializer):
    students = serializers.SerializerMethodField()

    class Meta:
        model = Institution
        fields = ["id", "name", "location", "website", "students"]
        read_only_fields = ["id", "students"]

    def get_students(self, obj):
        """Return the list of student names who are associated with this institution through education, projects, or courses"""
        # Get profile names from education records
        education_profiles = obj.educations.values_list("profile__name", flat=True)

        # Get profile names from projects associated with this institution
        project_profiles = getattr(
            obj, "projects", type("", (), {"values_list": lambda *args, **kwargs: []})
        ).values_list("profile__name", flat=True)

        # Get profile names from courses associated with this institution
        course_profiles = getattr(
            obj, "courses", type("", (), {"values_list": lambda *args, **kwargs: []})
        ).values_list("profile__name", flat=True)

        # Combine all profile names and remove duplicates
        all_profiles = (
            list(education_profiles) + list(project_profiles) + list(course_profiles)
        )
        return list(
            set(filter(None, all_profiles))
        )  # Remove None values and duplicates


class EducationSerializer(serializers.ModelSerializer):
    institution = InstitutionSerializer(read_only=True)
    institution_id = serializers.IntegerField(write_only=True, required=False)
    institution_data = InstitutionSerializer(write_only=True, required=False)
    degree_display = serializers.CharField(source="get_degree_display", read_only=True)

    class Meta:
        model = Education
        fields = [
            "id",
            "institution",
            "institution_id",
            "institution_data",
            "major",
            "degree",
            "degree_display",
            "series",
            "start_date",
            "end_date",
            "is_current",
            "description",
        ]
        read_only_fields = ["id", "degree_display"]
        write_only_fields = ["degree"]

    def validate(self, data):
        if data.get("end_date") and data.get("start_date"):
            if data["end_date"] < data["start_date"]:
                raise serializers.ValidationError(
                    "End date cannot be before start date."
                )

        # Validate institution fields
        institution_id = data.get("institution_id")
        institution_data = data.get("institution_data")

        if institution_id and institution_data:
            raise serializers.ValidationError(
                "Provide either institution_id OR institution_data, not both."
            )

        return data

    def create(self, validated_data):
        institution_data = validated_data.pop("institution_data", None)
        institution_id = validated_data.pop("institution_id", None)

        # Handle institution with priority: institution_id > institution_data
        if institution_id:
            # Use existing institution by ID
            try:
                institution = Institution.objects.get(id=institution_id)
                validated_data["institution"] = institution
            except Institution.DoesNotExist:
                raise serializers.ValidationError(
                    {"institution_id": "Institution with this ID does not exist."}
                )
        elif institution_data:
            # Create or get institution by name, location, and website
            institution, created = Institution.objects.get_or_create(
                name=institution_data["name"],
                location=institution_data.get("location"),
                website=institution_data.get("website"),
                defaults=institution_data,
            )
            validated_data["institution"] = institution

        education = Education.objects.create(**validated_data)
        return education

    def update(self, instance, validated_data):
        institution_data = validated_data.pop("institution_data", None)
        institution_id = validated_data.pop("institution_id", None)

        # Store the old institution for potential cleanup
        old_institution = instance.institution

        # Handle institution with priority: institution_id > institution_data
        if institution_id:
            # Use existing institution by ID
            try:
                institution = Institution.objects.get(id=institution_id)
                validated_data["institution"] = institution
            except Institution.DoesNotExist:
                raise serializers.ValidationError(
                    {"institution_id": "Institution with this ID does not exist."}
                )
        elif institution_data:
            # Create or get institution by name, location, and website
            institution, created = Institution.objects.get_or_create(
                name=institution_data["name"],
                location=institution_data.get("location"),
                website=institution_data.get("website"),
                defaults=institution_data,
            )
            validated_data["institution"] = institution

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Cleanup unused institution if it changed and has no other references
        self._cleanup_unused_institution(old_institution, instance.institution)

        return instance

    def _cleanup_unused_institution(self, old_institution, new_institution):
        """Clean up unused institution records when they're no longer referenced."""
        if old_institution and old_institution != new_institution:
            # Check if this institution is still referenced by other educations, projects, or courses
            education_count = Education.objects.filter(
                institution=old_institution
            ).count()
            project_count = old_institution.projects.count()
            course_count = old_institution.courses.count()

            # If no references exist, delete the institution
            if education_count == 0 and project_count == 0 and course_count == 0:
                old_institution.delete()


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]


class WorkOrganizationSerializer(serializers.ModelSerializer):
    workers = serializers.SerializerMethodField()

    class Meta:
        model = WorkOrganization
        fields = ["id", "name", "location", "website", "workers"]
        read_only_fields = ["id", "workers"]

    def get_workers(self, obj):
        """Return the list of worker names who have work experiences at this organization"""
        return list(
            obj.work_experiences.values_list("profile__name", flat=True).distinct()
        )


class WorkExperienceSerializer(serializers.ModelSerializer):
    organization = WorkOrganizationSerializer(read_only=True)
    organization_id = serializers.IntegerField(write_only=True, required=False)
    organization_data = WorkOrganizationSerializer(write_only=True, required=False)
    skills = SkillSerializer(many=True, read_only=True)
    skill_names = serializers.ListField(
        child=serializers.CharField(max_length=100),
        write_only=True,
        required=False,
        help_text="List of skill names",
    )
    experience_type_display = serializers.CharField(
        source="get_experience_type_display", read_only=True
    )

    class Meta:
        model = WorkExperience
        fields = [
            "id",
            "title",
            "organization",
            "organization_id",
            "organization_data",
            "experience_type",
            "experience_type_display",
            "description",
            "start_date",
            "end_date",
            "is_current",
            "skills",
            "skill_names",
        ]
        read_only_fields = ["id"]
        write_only_fields = ["experience_type"]

    def validate(self, data):
        if data.get("end_date") and data.get("start_date"):
            if data["end_date"] < data["start_date"]:
                raise serializers.ValidationError(
                    "End date cannot be before start date."
                )

        # Validate organization fields
        organization_id = data.get("organization_id")
        organization_data = data.get("organization_data")

        if organization_id and organization_data:
            raise serializers.ValidationError(
                "Provide either organization_id OR organization_data, not both."
            )

        return data

    def create(self, validated_data):
        skill_names = validated_data.pop("skill_names", [])
        organization_data = validated_data.pop("organization_data", None)
        organization_id = validated_data.pop("organization_id", None)

        # Handle organization with priority: organization_id > organization_data
        if organization_id:
            # Use existing organization by ID
            try:
                organization = WorkOrganization.objects.get(id=organization_id)
                validated_data["organization"] = organization
            except WorkOrganization.DoesNotExist:
                raise serializers.ValidationError(
                    {"organization_id": "Organization with this ID does not exist."}
                )
        elif organization_data:
            # Create or get organization by name, location, and website
            organization, created = WorkOrganization.objects.get_or_create(
                name=organization_data.get("name"),
                location=organization_data.get("location"),
                website=organization_data.get("website"),
                defaults=organization_data,
            )
            validated_data["organization"] = organization

        work_experience = WorkExperience.objects.create(
            **validated_data
        )  # Handle skills
        for skill_name in skill_names:
            skill, created = Skill.objects.get_or_create(name=skill_name.strip())
            work_experience.skills.add(skill)

        return work_experience

    def update(self, instance, validated_data):
        skill_names = validated_data.pop("skill_names", None)
        organization_data = validated_data.pop("organization_data", None)
        organization_id = validated_data.pop("organization_id", None)

        # Store the old organization for potential cleanup
        old_organization = instance.organization

        # Handle organization with priority: organization_id > organization_data
        if organization_id:
            # Use existing organization by ID
            try:
                organization = WorkOrganization.objects.get(id=organization_id)
                validated_data["organization"] = organization
            except WorkOrganization.DoesNotExist:
                raise serializers.ValidationError(
                    {"organization_id": "Organization with this ID does not exist."}
                )
        elif organization_data:
            # Create or get organization by name, location, and website
            organization, created = WorkOrganization.objects.get_or_create(
                name=organization_data["name"],
                location=organization_data.get("location"),
                website=organization_data.get("website"),
                defaults=organization_data,
            )
            validated_data["organization"] = organization

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Handle skills if provided
        if skill_names is not None:
            instance.skills.clear()
            for skill_name in skill_names:
                skill, created = Skill.objects.get_or_create(name=skill_name.strip())
                instance.skills.add(skill)

        # Cleanup unused organization if it changed and has no other references
        self._cleanup_unused_organization(old_organization, instance.organization)

        return instance

    def _cleanup_unused_organization(self, old_organization, new_organization):
        """
        Remove old organization if it's no longer referenced by any work experience
        and is different from the new organization.
        """
        if (
            old_organization
            and new_organization != old_organization
            and not old_organization.work_experiences.exists()
        ):
            old_organization.delete()


class ProjectSerializer(serializers.ModelSerializer):
    technologies = SkillSerializer(many=True, read_only=True)
    technology_names = serializers.ListField(
        child=serializers.CharField(max_length=100),
        write_only=True,
        required=False,
        help_text="List of technology/skill names",
    )
    collaborator_usernames = serializers.ListField(
        child=serializers.CharField(max_length=150),
        write_only=True,
        required=False,
        help_text="List of collaborator usernames",
    )
    collaborators = serializers.StringRelatedField(many=True, read_only=True)
    associated_institution = InstitutionSerializer(read_only=True)
    associated_institution_id = serializers.IntegerField(
        write_only=True, required=False
    )
    project_type_display = serializers.CharField(
        source="get_project_type_display", read_only=True
    )

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "description",
            "project_type",
            "project_type_display",
            "start_date",
            "end_date",
            "is_ongoing",
            "project_url",
            "github_url",
            "technologies",
            "technology_names",
            "collaborators",
            "collaborator_usernames",
            "associated_institution",
            "associated_institution_id",
        ]
        read_only_fields = ["id"]
        write_only_fields = ["project_type"]

    def validate(self, data):
        if data.get("end_date") and data.get("start_date"):
            if data["end_date"] < data["start_date"]:
                raise serializers.ValidationError(
                    "End date cannot be before start date."
                )
        return data

    def validate_collaborator_usernames(self, value):
        """Validate that all usernames exist and don't include self"""
        request = self.context.get("request")
        current_user = request.user if request else None

        for username in value:
            if not User.objects.filter(username=username).exists():
                raise serializers.ValidationError(
                    f"User with username '{username}' does not exist."
                )

            # Prevent self-collaboration (optional - could be allowed)
            if current_user and username == current_user.username:
                raise serializers.ValidationError(
                    "You cannot add yourself as a collaborator."
                )
        return value

    def validate_associated_institution_id(self, value):
        """Validate that institution belongs to the user's profile"""
        if value:
            request = self.context.get("request")
            if request and hasattr(request, "user"):
                if not Institution.objects.filter(
                    id=value, profile=request.user.profile
                ).exists():
                    raise serializers.ValidationError(
                        "Institution not found in your profile."
                    )
        return value

    def create(self, validated_data):
        technology_names = validated_data.pop("technology_names", [])
        collaborator_usernames = validated_data.pop("collaborator_usernames", [])
        associated_institution_id = validated_data.pop(
            "associated_institution_id", None
        )

        if associated_institution_id:
            validated_data["associated_institution_id"] = associated_institution_id

        project = Project.objects.create(**validated_data)  # Handle technologies
        for tech_name in technology_names:
            skill, created = Skill.objects.get_or_create(name=tech_name.strip())
            project.technologies.add(skill)

        # Handle collaborators
        for username in collaborator_usernames:
            user = User.objects.get(username=username)
            project.collaborators.add(user)

        return project

    def update(self, instance, validated_data):
        technology_names = validated_data.pop("technology_names", None)
        collaborator_usernames = validated_data.pop("collaborator_usernames", None)
        associated_institution_id = validated_data.pop(
            "associated_institution_id", None
        )

        if associated_institution_id:
            validated_data["associated_institution_id"] = associated_institution_id

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()  # Handle technologies if provided
        if technology_names is not None:
            instance.technologies.clear()
            for tech_name in technology_names:
                skill, created = Skill.objects.get_or_create(name=tech_name.strip())
                instance.technologies.add(skill)

        # Handle collaborators if provided
        if collaborator_usernames is not None:
            instance.collaborators.clear()
            for username in collaborator_usernames:
                user = User.objects.get(username=username)
                instance.collaborators.add(user)

        return instance


class AchievementSerializer(serializers.ModelSerializer):
    achievement_type_display = serializers.CharField(
        source="get_achievement_type_display", read_only=True
    )

    class Meta:
        model = Achievement
        fields = [
            "id",
            "title",
            "description",
            "achievement_type",
            "achievement_type_display",
            "issuer",
            "date_received",
            "url",
        ]
        read_only_fields = ["id", "achievement_type_display"]
        write_only_fields = ["achievement_type"]


class CourseSerializer(serializers.ModelSerializer):
    skills_learned = SkillSerializer(many=True, read_only=True)
    skill_names = serializers.ListField(
        child=serializers.CharField(max_length=100),
        write_only=True,
        required=False,
        help_text="List of skill names learned",
    )
    associated_institution = InstitutionSerializer(read_only=True)
    associated_institution_id = serializers.IntegerField(
        write_only=True, required=False
    )

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "provider",
            "description",
            "completion_date",
            "certificate_url",
            "skills_learned",
            "skill_names",
            "associated_institution",
            "associated_institution_id",
        ]
        read_only_fields = ["id"]

    def validate_associated_institution_id(self, value):
        """Validate that institution belongs to the user's profile"""
        if value:
            request = self.context.get("request")
            if request and hasattr(request, "user"):
                if not Institution.objects.filter(
                    id=value, profile=request.user.profile
                ).exists():
                    raise serializers.ValidationError(
                        "Institution not found in your profile."
                    )
        return value

    def create(self, validated_data):
        skill_names = validated_data.pop("skill_names", [])
        associated_institution_id = validated_data.pop(
            "associated_institution_id", None
        )

        if associated_institution_id:
            validated_data["associated_institution_id"] = associated_institution_id

        course = Course.objects.create(**validated_data)  # Handle skills
        for skill_name in skill_names:
            skill, created = Skill.objects.get_or_create(name=skill_name.strip())
            course.skills_learned.add(skill)

        return course

    def update(self, instance, validated_data):
        skill_names = validated_data.pop("skill_names", None)
        associated_institution_id = validated_data.pop(
            "associated_institution_id", None
        )

        if associated_institution_id:
            validated_data["associated_institution_id"] = associated_institution_id

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()  # Handle skills if provided
        if skill_names is not None:
            instance.skills_learned.clear()
            for skill_name in skill_names:
                skill, created = Skill.objects.get_or_create(name=skill_name.strip())
                instance.skills_learned.add(skill)

        return instance


class InterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interest
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]


class PublicationSerializer(serializers.ModelSerializer):
    publication_type_display = serializers.CharField(
        source="get_publication_type_display", read_only=True
    )

    class Meta:
        model = Publication
        fields = [
            "id",
            "title",
            "description",
            "publication_type",
            "publication_type_display",
            "authors",
            "publication_date",
            "url",
        ]
        read_only_fields = ["id"]
        write_only_fields = ["publication_type"]


class ProfileSerializer(serializers.ModelSerializer):
    educations = EducationSerializer(many=True, read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    work_experiences = WorkExperienceSerializer(many=True, read_only=True)
    projects = ProjectSerializer(many=True, read_only=True)
    achievements = AchievementSerializer(many=True, read_only=True)
    publications = PublicationSerializer(many=True, read_only=True)
    courses = CourseSerializer(many=True, read_only=True)
    interests = InterestSerializer(many=True, read_only=True)
    gender_display = serializers.CharField(source="get_gender_display", read_only=True)

    class Meta:
        model = Profile
        fields = [
            "name",
            "bio",
            "about_me",
            "address",
            "personal_website",
            "gender",
            "gender_display",
            "profile_pic",
            "created_at",
            "educations",
            "skills",
            "work_experiences",
            "projects",
            "achievements",
            "publications",
            "courses",
            "interests",
        ]
        read_only_fields = ["created_at"]
        write_only_fields = ["gender"]


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "profile"]
