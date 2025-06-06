# Generated migration to convert Skill and Interest from ForeignKey to ManyToMany
from django.db import migrations, models


def migrate_skills_and_interests(apps, schema_editor):
    """
    Migrate existing skills and interests from ForeignKey to ManyToMany
    Handle duplicate names by consolidating them
    """
    Profile = apps.get_model("users", "Profile")
    Skill = apps.get_model("users", "Skill")
    Interest = apps.get_model("users", "Interest")

    # Create a mapping of skills/interests to profiles, handling duplicates
    skill_profile_mapping = []
    interest_profile_mapping = []

    # Dictionary to track unique skills and their associated profiles
    unique_skills = {}
    unique_interests = {}

    # Process skills and consolidate duplicates
    for skill in Skill.objects.all():
        skill_name = skill.name
        if skill_name not in unique_skills:
            unique_skills[skill_name] = {"id": skill.id, "profiles": [skill.profile_id]}
        else:
            # Add profile to existing skill and mark duplicate for deletion
            unique_skills[skill_name]["profiles"].append(skill.profile_id)
            # Delete duplicate skill
            skill.delete()

    # Process interests (no duplicates found, but handle just in case)
    for interest in Interest.objects.all():
        interest_name = interest.name
        if interest_name not in unique_interests:
            unique_interests[interest_name] = {
                "id": interest.id,
                "profiles": [interest.profile_id],
            }
        else:
            # Add profile to existing interest and mark duplicate for deletion
            unique_interests[interest_name]["profiles"].append(interest.profile_id)
            # Delete duplicate interest
            interest.delete()

    # Store the consolidated mappings
    for skill_name, data in unique_skills.items():
        for profile_id in data["profiles"]:
            skill_profile_mapping.append((data["id"], profile_id))

    for interest_name, data in unique_interests.items():
        for profile_id in data["profiles"]:
            interest_profile_mapping.append((data["id"], profile_id))

    # Store the mappings in the migration state
    migrate_skills_and_interests.skill_mappings = skill_profile_mapping
    migrate_skills_and_interests.interest_mappings = interest_profile_mapping


def reverse_migrate_skills_and_interests(apps, schema_editor):
    """
    Reverse migration - restore ForeignKey relationships
    """
    Profile = apps.get_model("users", "Profile")
    Skill = apps.get_model("users", "Skill")
    Interest = apps.get_model("users", "Interest")

    # Restore the original profile relationships
    if hasattr(reverse_migrate_skills_and_interests, "skill_mappings"):
        for skill_id, profile_id in reverse_migrate_skills_and_interests.skill_mappings:
            try:
                skill = Skill.objects.get(id=skill_id)
                skill.profile_id = profile_id
                skill.save()
            except Skill.DoesNotExist:
                pass

    if hasattr(reverse_migrate_skills_and_interests, "interest_mappings"):
        for (
            interest_id,
            profile_id,
        ) in reverse_migrate_skills_and_interests.interest_mappings:
            try:
                interest = Interest.objects.get(id=interest_id)
                interest.profile_id = profile_id
                interest.save()
            except Interest.DoesNotExist:
                pass


def connect_manytomany_relationships(apps, schema_editor):
    """
    Connect the new ManyToMany relationships based on old ForeignKey data
    """
    Profile = apps.get_model("users", "Profile")
    Skill = apps.get_model("users", "Skill")
    Interest = apps.get_model("users", "Interest")

    # Use the stored mappings to create ManyToMany relationships
    if hasattr(migrate_skills_and_interests, "skill_mappings"):
        for skill_id, profile_id in migrate_skills_and_interests.skill_mappings:
            try:
                skill = Skill.objects.get(id=skill_id)
                profile = Profile.objects.get(id=profile_id)
                profile.skills.add(skill)
            except (Skill.DoesNotExist, Profile.DoesNotExist):
                pass

    if hasattr(migrate_skills_and_interests, "interest_mappings"):
        for interest_id, profile_id in migrate_skills_and_interests.interest_mappings:
            try:
                interest = Interest.objects.get(id=interest_id)
                profile = Profile.objects.get(id=profile_id)
                profile.interests.add(interest)
            except (Interest.DoesNotExist, Profile.DoesNotExist):
                pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0010_profile_profile_memory_profile_profile_summary_and_more"),
    ]

    operations = [
        # Step 1: Store existing relationships
        migrations.RunPython(
            migrate_skills_and_interests,
            reverse_migrate_skills_and_interests,
        ),
        # Step 2: Remove unique_together constraints
        migrations.AlterUniqueTogether(
            name="interest",
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name="skill",
            unique_together=set(),
        ),
        # Step 3: Add ManyToMany fields to Profile
        migrations.AddField(
            model_name="profile",
            name="interests",
            field=models.ManyToManyField(
                blank=True, related_name="profiles", to="users.interest"
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="skills",
            field=models.ManyToManyField(
                blank=True, related_name="profiles", to="users.skill"
            ),
        ),
        # Step 4: Make name fields unique
        migrations.AlterField(
            model_name="interest",
            name="name",
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name="skill",
            name="name",
            field=models.CharField(max_length=100, unique=True),
        ),
        # Step 5: Connect ManyToMany relationships
        migrations.RunPython(
            connect_manytomany_relationships,
            migrations.RunPython.noop,
        ),
        # Step 6: Remove old ForeignKey fields
        migrations.RemoveField(
            model_name="interest",
            name="profile",
        ),
        migrations.RemoveField(
            model_name="skill",
            name="profile",
        ),
    ]
