from django.conf import settings
from django.db import models


class Conversation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",  # eta to serialize korar dorkar nai tai na
    )
    title = models.CharField(max_length=255, blank=True)
    summary = models.TextField(blank=True)  # for memory, will be used later
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conversation #{self.pk} ({self.user})"


class Message(models.Model):
    SENDER_CHOICES = [
        ("user", "User"),
        ("bot", "Bot"),
    ]
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} @ {self.timestamp:%Y-%m-%d %H:%M:%S}"
