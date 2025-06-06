from django.contrib.auth.models import User
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Education, Institution, Profile, WorkExperience, WorkOrganization


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_delete, sender=WorkExperience)
def cleanup_unused_organization(sender, instance, **kwargs):
    """
    Clean up WorkOrganization records that are no longer referenced
    by any WorkExperience after a work experience is deleted.
    """
    try:
        # Check if the instance still has an organization_id
        if hasattr(instance, "organization_id") and instance.organization_id:
            try:
                # Try to get the organization by ID instead of through the relationship
                organization = WorkOrganization.objects.get(id=instance.organization_id)

                # Check if this organization is still referenced by other work experiences
                if not organization.work_experiences.exists():
                    organization.delete()
            except WorkOrganization.DoesNotExist:
                # Organization already deleted, nothing to do
                pass
    except (AttributeError, TypeError):
        # Instance doesn't have organization_id or other attribute error, nothing to do
        pass


@receiver(post_delete, sender=Education)
def cleanup_unused_institution(sender, instance, **kwargs):
    """
    Clean up Institution records that are no longer referenced
    by any Education, Project, or Course after an education is deleted.
    """
    try:
        # Check if the instance still has an institution_id
        if hasattr(instance, "institution_id") and instance.institution_id:
            try:
                # Try to get the institution by ID instead of through the relationship
                institution = Institution.objects.get(id=instance.institution_id)

                # Check if this institution is still referenced by other records
                education_count = institution.educations.count()
                # Use safe attribute access for projects and courses (they might not exist yet)
                project_count = getattr(
                    institution, "projects", type("", (), {"count": lambda: 0})
                )().count()
                course_count = getattr(
                    institution, "courses", type("", (), {"count": lambda: 0})
                )().count()

                # If no references exist, delete the institution
                if education_count == 0 and project_count == 0 and course_count == 0:
                    institution.delete()
            except Institution.DoesNotExist:
                # Institution already deleted, nothing to do
                pass
    except (AttributeError, TypeError):
        # Instance doesn't have institution_id or other attribute error, nothing to do
        pass
