from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    interests = models.JSONField(default=list)  # e.g., ["AI", "Math"]
    profile_image = models.ImageField(upload_to="profiles/", null=True, blank=True)
    peers = models.ManyToManyField(
        "self", symmetrical=False, related_name="peer_of", blank=True
    )

    def __str__(self):
        return f"{self.user.username}'s profile"
