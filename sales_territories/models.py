from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

AUTH_USER_MODEL = settings.AUTH_USER_MODEL


class Territory(models.Model):
    """Represents a sales territory"""
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Name of the sales territory"),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Optional description for the territory"),
    )
    manager = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='managed_territories',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("Manager responsible for this territory (Optional)"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Territory")
        verbose_name_plural = _("Territories")
        ordering = ['name']

    def __str__(self):
        return self.name