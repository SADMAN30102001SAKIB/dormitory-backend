from django.core.management.base import BaseCommand
from users.models import Profile
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Clears all user interest embedding vectors from user profiles."

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING("Starting to clear all user interest embeddings...")
        )

        profiles = Profile.objects.all()
        cleared_count = 0

        for profile in profiles:
            if profile.users_embedding:
                profile.users_embedding = ""
                profile.save(update_fields=["users_embedding"])
                cleared_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully cleared {cleared_count} user interest embeddings."
            )
        )
