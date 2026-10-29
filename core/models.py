from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base class: common timestamp fields shared by many models."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserRelatedModel(models.Model):
    """Abstract base class: models that are associated with a user/guest."""

    user = models.ForeignKey(
        'auth.User', on_delete=models.CASCADE, related_name='%(app_label)s_%(class)s_set'
    )

    class Meta:
        abstract = True
