"""
Base models for the enterprise platform.
"""

import uuid

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base class that provides self-updating created_at and updated_at fields.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeletableModel(models.Model):
    """
    Abstract base class that provides soft delete functionality.
    """

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_by = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        abstract = True

    def delete(self, using: str | None = None) -> None:
        """
        Override delete to perform soft delete instead of actual deletion.
        """
        self.deleted_at = timezone.now()
        self.save(using=using)

    def hard_delete(self, using: str | None = None) -> None:
        """
        Perform actual deletion of the object.
        """
        super().delete(using=using)

    @classmethod
    def get_active(cls) -> models.QuerySet:
        """
        Return queryset excluding soft-deleted objects.
        """
        return cls.objects.filter(deleted_at__isnull=True)

    @classmethod
    def get_deleted(cls) -> models.QuerySet:
        """
        Return queryset including only soft-deleted objects.
        """
        return cls.objects.filter(deleted_at__isnull=False)


class CoreModel(TimeStampedModel, SoftDeletableModel):
    """
    Base model with UUID pk, timestamps, and soft delete.
    Use for platform-level models that don't belong to a tenant.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True

    def get_absolute_url(self) -> str:
        """
        Return the absolute URL for the object.
        Override in child classes.
        """
        return f"/api/{self.__class__.__name__.lower()}s/{self.pk}/"


class BaseModel(CoreModel):
    """
    Default model for all tenant-scoped resources.
    """

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
        db_index=True,
    )

    class Meta:
        abstract = True
