from django.db import models
from django.contrib.auth.models import User
from users.models import Institution


class Domain(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="domains")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    institution = models.ForeignKey(
        Institution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productivity_domains",
    )

    def __str__(self):
        return self.name


class TrackedTime(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="tracked_times"
    )
    domain = models.ForeignKey(
        "Domain",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tracked_times",
    )
    goal = models.CharField(
        max_length=255, blank=True, null=True
    )  # session description
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)

    def __str__(self):
        return f"Tracked time for {self.domain.name if self.domain else 'General'} with goal: {self.goal}"

    def save(self, *args, **kwargs):
        if self.end_time and self.start_time:
            self.duration = self.end_time - self.start_time
        super().save(*args, **kwargs)
