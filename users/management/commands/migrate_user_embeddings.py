import json
import logging
from django.core.management.base import BaseCommand
from users.models import Profile
from users.user_vectorstore_utils import add_or_update_user_embedding
import numpy as np

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migrates user embeddings from the Profile model to the Chroma vector store."

    def handle(self, *args, **options):
        self.stdout.write("Starting user embedding migration...")
        profiles = Profile.objects.all()
        migrated_count = 0
        for profile in profiles:
            if profile.users_embedding:
                try:
                    embedding_list = json.loads(profile.users_embedding)
                    embedding_vector = np.array(
                        embedding_list
                    ).tolist()  # Ensure it's a list for the function
                    add_or_update_user_embedding(profile.user, embedding_vector)
                    migrated_count += 1
                except (json.JSONDecodeError, TypeError) as e:
                    self.stderr.write(
                        self.style.ERROR(
                            f"Could not migrate embedding for user {profile.user.username}: {e}"
                        )
                    )
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully migrated {migrated_count} user embeddings."
            )
        )
