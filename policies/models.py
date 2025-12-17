from django.db import models
from django.conf import settings


class UserGroup(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Policy(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()

    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    groups = models.ManyToManyField(
        UserGroup,
        through='PolicyAudience',
        related_name='policies'
    )

    def __str__(self):
        return self.title


class PolicyAudience(models.Model):
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE
    )
    group = models.ForeignKey(
        UserGroup,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f"{self.policy.title} - {self.group.name}"


class PolicyAcknowledgement(models.Model):
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name='acknowledgements'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    acknowledged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('policy', 'user')

    def __str__(self):
        return f"{self.user} acknowledged {self.policy.title}"
