# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _ # For translations later if needed

class CustomUser(AbstractUser):
    """
    Extends the default Django User model.
    Uses email as the unique identifier instead of username by default
    (from AbstractUser). Adds Role and Phone Number.
    """
    class Roles(models.TextChoices):
        ADMIN = 'ADMIN', _('Admin')
        MANAGER = 'MANAGER', _('Manager')
        SALES = 'SALES', _('Sales Associate')

    # We keep username/email/first/last name fields from AbstractUser
    # Add our custom fields:
    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.SALES, # Default new users to Sales role
        help_text=_('Designates the role of the user within the CRM.')
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True, # Allow phone number to be optional
        help_text=_('User contact phone number.')
    )

    # Future field (depends on Milestone 400):
    territory = models.ForeignKey(
        'sales_territories.Territory', # Use string to avoid circular import now
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='team_members',
        help_text=_('Sales territory this user belongs to, if applicable.')
    )

    # You might want to add other fields later, like profile picture, etc.

    def __str__(self):
        return self.get_full_name() or self.username

    # Add properties for easy role checking later in templates/views (optional but helpful)
    @property
    def is_admin_role(self):
        return self.role == self.Roles.ADMIN

    @property
    def is_manager_role(self):
        return self.role == self.Roles.MANAGER

    @property
    def is_sales_role(self):
        return self.role == self.Roles.SALES