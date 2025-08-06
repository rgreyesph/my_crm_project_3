from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import URLValidator

AUTH_USER_MODEL = settings.AUTH_USER_MODEL

class StatusChoices(models.TextChoices):
    ACTIVE = 'ACTIVE', _('Active')
    INACTIVE = 'INACTIVE', _('Inactive')
    PROSPECT = 'PROSPECT', _('Prospect')
    CUSTOMER = 'CUSTOMER', _('Customer')
    PARTNER = 'PARTNER', _('Partner')
    FORMER = 'FORMER', _('Former Customer')

class Account(models.Model):
    """Represents a client company or organization"""
    # Required Field:
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text=_("Name of the client company"),
    )

    # Optional Fields:
    website = models.URLField(
        max_length=255,
        blank=True,
        null=True,
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Enter a valid phone number (e.g., +6388019525).',
            )
        ],
    )
    billing_address = models.TextField(blank=True)
    shipping_address = models.TextField(blank=True)
    industry = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("e.g., Technology, Finance, Healthcare"),
    )
    status = models.CharField(
        max_length=50,
        choices=StatusChoices.choices,
        default=StatusChoices.PROSPECT,
        blank=True,
    )
    territory = models.ForeignKey(
        'sales_territories.Territory',
        related_name='accounts_in_territory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("Territory this account belongs to (Optional)"),
    )
    assigned_to = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='assigned_accounts',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("Sales Associate primarily responsible for this account"),
    )

    # System Fields (generally not user-editable directly)
    created_by = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='created_accounts',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,  # Keep blank=True for admin/logic
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Account")
        verbose_name_plural = _("Accounts")
        ordering = ['name']

    def __str__(self):
        return self.name


class Contact(models.Model):
    """Represents an individual contact person, usually associated with an Account"""
    # Required Field:
    last_name = models.CharField(max_length=100)

    # Optional Fields:
    account = models.ForeignKey(
        Account,
        related_name='contacts',
        on_delete=models.CASCADE,
        null=True,
        blank=True,  # Already optional
    )
    first_name = models.CharField(
        max_length=100,
        blank=True,
    )  # Added blank=True
    title = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("e.g., CEO, Marketing Manager"),
    )
    department = models.CharField(max_length=100, blank=True)
    email = models.EmailField(
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                message='Enter a valid email address (e.g., user@example.com).',
            )
        ],
    )
    work_phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Enter a valid phone number (e.g., +6388019525).',
            )
        ],
    )
    mobile_phone_1 = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Enter a valid phone number (e.g., +639088835511).',
            )
        ],
    )
    mobile_phone_2 = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Enter a valid phone number (e.g., +639088835511).',
            )
        ],
    )
    notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='assigned_contacts',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,  # Already optional
    )

    # System Fields
    created_by = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='created_contacts',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Contact")
        verbose_name_plural = _("Contacts")
        ordering = ['account', 'last_name', 'first_name']

    def __str__(self):
        # Handle cases where first name might be blank
        return f"{self.first_name} {self.last_name}".strip() or self.last_name

    @property
    def full_name(self):
        # Handle cases where first name might be blank
        return f"{self.first_name} {self.last_name}".strip() or self.last_name


class Lead(models.Model):
    """Represents a potential prospect before they become a qualified Contact/Account"""
    class StatusChoices(models.TextChoices):
        NEW = 'NEW', _('New')
        CONTACTED = 'CONTACTED', _('Contacted')
        QUALIFIED = 'QUALIFIED', _('Qualified')
        LOST = 'LOST', _('Lost')
        CONVERTED = 'CONVERTED', _('Converted')

    class SourceChoices(models.TextChoices):
        WEBSITE = 'WEBSITE', _('Website')
        REFERRAL = 'REFERRAL', _('Referral')
        COLD_CALL = 'COLD_CALL', _('Cold Call')
        EVENT = 'EVENT', _('Event')
        OTHER = 'OTHER', _('Other')

    # Required Field:
    last_name = models.CharField(max_length=100)

    # Optional Fields:
    first_name = models.CharField(
        max_length=100,
        blank=True,
    )  # Added blank=True
    company_name = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    email = models.EmailField(
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                message='Enter a valid email address (e.g., user@example.com).',
            )
        ],
    )
    work_phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Enter a valid phone number (e.g., +6388019525).',
            )
        ],
    )
    mobile_phone_1 = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Enter a valid phone number (e.g., +6388019525).',
            )
        ],
    )
    mobile_phone_2 = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Enter a valid phone number (e.g., +6388019525).',
            )
        ],
    )
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(  # Has default, allow blank? Keep default for now
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.NEW,
    )
    source = models.CharField(  # Allow blank source
        max_length=20,
        choices=SourceChoices.choices,
        blank=True,
    )
    territory = models.ForeignKey(
        'sales_territories.Territory',
        related_name='leads_in_territory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,  # Already optional
    )
    assigned_to = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='assigned_leads',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,  # Already optional
        help_text=_("Sales Associate responsible for this lead"),
    )

    # System Fields
    created_by = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='created_leads',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Lead")
        verbose_name_plural = _("Leads")
        ordering = ['-created_at']

    def __str__(self):
        # Handle cases where first name might be blank
        return f"{self.first_name} {self.last_name}".strip() or self.last_name

    @property
    def full_name(self):
        # Handle cases where first name might be blank
        return f"{self.first_name} {self.last_name}".strip() or self.last_name