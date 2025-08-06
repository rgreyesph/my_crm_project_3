from datetime import timedelta
from datetime import date
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

AUTH_USER_MODEL = settings.AUTH_USER_MODEL


class SalesTarget(models.Model):
    """Stores sales target/quota information for users over specific periods"""
    user = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='sales_targets',
        on_delete=models.CASCADE,
        help_text=_("The sales user this target applies to"),
    )
    target_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text=_("The target sales amount (e.g., in PHP) for the period"),
    )
    start_date = models.DateField(
        help_text=_("The first day of the target period")
    )
    end_date = models.DateField(
        help_text=_("The last day of the target period")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Sales Target")
        verbose_name_plural = _("Sales Targets")
        ordering = ['user', '-start_date']
        # constraints = [
        #     models.UniqueConstraint(
        #         fields=['user', 'start_date'],
        #         name='unique_user_start_date'
        #     ),
        #     models.UniqueConstraint(
        #         fields=['user', 'end_date'],
        #         name='unique_user_end_date'
        #     ),
        # ]

    def __str__(self):
        return (
            f"{self.user.username} Target: {self.target_amount} "
            f"({self.start_date} to {self.end_date})"
        )

    def clean(self):
        if (
            self.start_date and
            self.end_date and
            self.end_date < self.start_date
        ):
            raise ValidationError(
                _('End date cannot be before start date.')
            )

    @property
    def period_description(self):
        # Calculate next month's first day, handling December (month=12 -> year+1, month=1)
        if self.start_date.month == 12:
            next_year = self.start_date.year + 1
            next_month = 1
        else:
            next_year = self.start_date.year
            next_month = self.start_date.month + 1
        next_month_first = date(next_year, next_month, 1)
        last_day_of_month = (next_month_first - timedelta(days=1)).day

        if self.start_date.day == 1 and self.end_date.day == last_day_of_month:
            return self.start_date.strftime('%b %Y')
        return (
            f"{self.start_date.strftime('%Y-%m-%d')} to "
            f"{self.end_date.strftime('%Y-%m-%d')}"
        )