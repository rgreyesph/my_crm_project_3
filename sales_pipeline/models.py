from datetime import timedelta
import re

from django.conf import settings
from django.db import models
from django.db.models import Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from crm_entities.models import Account, Contact

AUTH_USER_MODEL = settings.AUTH_USER_MODEL


class Deal(models.Model):
    """Represents a potential sale or Opportunity"""
    class StageChoices(models.TextChoices):
        PROSPECTING = 'PROSPECTING', _('Prospecting')
        QUALIFICATION = 'QUALIFICATION', _('Qualification')
        PROPOSAL = 'PROPOSAL', _('Proposal/Quote Sent')
        NEGOTIATION = 'NEGOTIATION', _('Negotiation')
        CLOSED_WON = 'CLOSED_WON', _('Closed Won')
        CLOSED_LOST = 'CLOSED_LOST', _('Closed Lost')

    STAGE_PROBABILITY_MAP = {
        StageChoices.PROSPECTING: 10,
        StageChoices.QUALIFICATION: 25,
        StageChoices.PROPOSAL: 60,
        StageChoices.NEGOTIATION: 80,
        StageChoices.CLOSED_WON: 100,
        StageChoices.CLOSED_LOST: 0,
    }

    deal_id = models.CharField(
        _("Deal ID"),
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        editable=False,
        help_text=_("Unique identifier (e.g., D25-00001)"),
    )
    name = models.CharField(
        max_length=255,
        help_text=_("Name or title of the deal"),
    )
    account = models.ForeignKey(
        Account,
        related_name='deals',
        on_delete=models.CASCADE,
        help_text=_("The account this deal is associated with"),
    )
    primary_contact = models.ForeignKey(
        Contact,
        related_name='deals',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("Primary contact person for this deal (Optional)"),
    )
    stage = models.CharField(
        max_length=20,
        choices=StageChoices.choices,
        default=StageChoices.PROSPECTING,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text=_("Estimated or actual value of the deal"),
    )
    currency = models.CharField(
        max_length=3,
        default='PHP',
        help_text=_("Currency code (e.g., PHP, USD)"),
    )
    close_date = models.DateField(
        help_text=_("Expected or actual closing date")
    )
    probability = models.IntegerField(
        default=10,
        editable=False,
        help_text=_("Probability of closing (determined by Stage)"),
    )
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='created_deals',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    assigned_to = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='assigned_deals',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Deal / Opportunity")
        verbose_name_plural = _("Deals / Opportunities")
        ordering = ['-close_date', '-updated_at']

    def __str__(self):
        deal_identifier = (
            self.deal_id or f"Deal #{self.pk or 'New'}"
        )
        account_name = (
            self.account.name if self.account else "No Account"
        )
        return f"{deal_identifier}: {self.name} ({account_name})"

    def save(self, *args, **kwargs):
        self.probability = self.STAGE_PROBABILITY_MAP.get(self.stage, 0)

        if not self.deal_id:
            now = timezone.now()
            year_str = now.strftime('%y')
            prefix = f"D{year_str}-"
            try:
                last_deal = Deal.objects.filter(
                    deal_id__startswith=prefix
                ).aggregate(max_id=Max('deal_id'))
                if last_deal and last_deal.get('max_id'):
                    match = re.match(rf"D\d\d-(\d+)", last_deal['max_id'])
                    if match:
                        last_num = int(match.group(1))
                        new_num = last_num + 1
                    else:
                        new_num = 1
                else:
                    new_num = 1
                self.deal_id = f"{prefix}{new_num:05d}"
            except Exception as e:
                print(f"Error generating deal_id: {e}")

        super().save(*args, **kwargs)


class Quote(models.Model):
    """Represents a formal price quote provided to a potential customer"""
    class StatusChoices(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        PRESENTED = 'PRESENTED', _('Presented')
        ACCEPTED = 'ACCEPTED', _('Accepted')
        REJECTED = 'REJECTED', _('Rejected')

    quote_id = models.CharField(
        _("Quote ID"),
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        editable=False,
        help_text=_("Unique identifier (e.g., Q-25-00001)"),
    )
    deal = models.ForeignKey(
        Deal,
        related_name='quotes',
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        help_text=_("Deal this quote is associated with"),
    )
    account = models.ForeignKey(
        'crm_entities.Account',
        related_name='quotes',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        editable=False,
        help_text=_("Account the quote is for (derived from Deal)"),
    )
    contact = models.ForeignKey(
        'crm_entities.Contact',
        related_name='quotes',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("Contact person the quote is addressed to (Optional)"),
    )
    presented_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date the quote was presented to the client"),
    )
    validity_days = models.PositiveIntegerField(
        default=30,
        help_text=_("Number of days the quote is valid after presentation date"),
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Total amount of the quote"),
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='created_quotes',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    assigned_to = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='assigned_quotes',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Quote")
        verbose_name_plural = _("Quotes")
        ordering = ['-created_at']

    def __str__(self):
        return self.quote_id or f"Quote #{self.pk or 'New'}"

    @property
    def expiry_date(self):
        if self.presented_date and self.validity_days is not None:
            try:
                return self.presented_date + timedelta(
                    days=int(self.validity_days)
                )
            except (TypeError, ValueError):
                return None
        return None

    def save(self, *args, **kwargs):
        if self.deal and self.deal.account:
            self.account = self.deal.account

        if not self.quote_id:
            now = timezone.now()
            year_str = now.strftime('%y')
            prefix = f"Q{year_str}-"
            try:
                last_quote = Quote.objects.filter(
                    quote_id__startswith=prefix
                ).aggregate(max_id=Max('quote_id'))
                if last_quote and last_quote.get('max_id'):
                    match = re.match(rf"Q\d\d-(\d+)", last_quote['max_id'])
                    if match:
                        last_num = int(match.group(1))
                        new_num = last_num + 1
                    else:
                        new_num = 1
                else:
                    new_num = 1
                self.quote_id = f"{prefix}{new_num:05d}"
            except Exception as e:
                print(f"Error generating quote_id: {e}")

        super().save(*args, **kwargs)