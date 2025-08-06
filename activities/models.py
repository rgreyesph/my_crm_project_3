from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

AUTH_USER_MODEL = settings.AUTH_USER_MODEL


class TaskStatusChoices(models.TextChoices):
    NOT_STARTED = 'NOT_STARTED', _('Not Started')
    IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
    COMPLETED = 'COMPLETED', _('Completed')
    DEFERRED = 'DEFERRED', _('Deferred')


class TaskPriorityChoices(models.TextChoices):
    LOW = 'LOW', _('Low')
    NORMAL = 'NORMAL', _('Normal')
    HIGH = 'HIGH', _('High')


class Task(models.Model):
    """Represents a task to be completed"""
    subject = models.CharField(max_length=255)
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date the task is expected to be completed"),
    )
    status = models.CharField(
        max_length=20,
        choices=TaskStatusChoices.choices,
        default=TaskStatusChoices.NOT_STARTED,
    )
    priority = models.CharField(
        max_length=20,
        choices=TaskPriorityChoices.choices,
        default=TaskPriorityChoices.NORMAL,
    )
    description = models.TextField(blank=True)

    related_to_account = models.ForeignKey(
        'crm_entities.Account',
        related_name='tasks',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Related Account"),
    )
    related_to_contact = models.ForeignKey(
        'crm_entities.Contact',
        related_name='tasks',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Related Contact"),
    )
    related_to_lead = models.ForeignKey(
        'crm_entities.Lead',
        related_name='tasks',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Related Lead"),
    )
    related_to_deal = models.ForeignKey(
        'sales_pipeline.Deal',
        related_name='tasks',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Related Deal"),
    )

    created_by = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='created_tasks',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    assigned_to = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='assigned_tasks',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("User responsible for completing the task"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Task")
        verbose_name_plural = _("Tasks")
        ordering = ['due_date', 'priority']

    def __str__(self):
        return self.subject


class CallDirectionChoices(models.TextChoices):
    INCOMING = 'INCOMING', _('Incoming')
    OUTGOING = 'OUTGOING', _('Outgoing')


class CallMeetingStatusChoices(models.TextChoices):
    PLANNED = 'PLANNED', _('Planned')
    HELD = 'HELD', _('Held')
    NOT_HELD = 'NOT_HELD', _('Not Held / Cancelled')


class Call(models.Model):
    """Represents a phone call activity"""
    subject = models.CharField(
        max_length=255,
        help_text=_("Purpose of the call"),
    )
    call_time = models.DateTimeField(
        default=timezone.now,
        help_text=_("Scheduled or actual time of call"),
    )
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Duration of the call in minutes"),
    )
    direction = models.CharField(
        max_length=10,
        choices=CallDirectionChoices.choices,
        default=CallDirectionChoices.OUTGOING,
    )
    status = models.CharField(
        max_length=20,
        choices=CallMeetingStatusChoices.choices,
        default=CallMeetingStatusChoices.PLANNED,
    )
    notes = models.TextField(blank=True)

    related_to_account = models.ForeignKey(
        'crm_entities.Account',
        related_name='calls',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Related Account"),
    )
    related_to_contact = models.ForeignKey(
        'crm_entities.Contact',
        related_name='calls',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Related Contact"),
    )
    related_to_lead = models.ForeignKey(
        'crm_entities.Lead',
        related_name='calls',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Related Lead"),
    )
    related_to_deal = models.ForeignKey(
        'sales_pipeline.Deal',
        related_name='calls',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Related Deal"),
    )

    created_by = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='created_calls',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    assigned_to = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='assigned_calls',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("User who made or is primarily associated with the call"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Call")
        verbose_name_plural = _("Calls")
        ordering = ['-call_time']

    def __str__(self):
        return f"{self.subject} ({self.get_direction_display()})"


class Meeting(models.Model):
    """Represents a meeting activity"""
    subject = models.CharField(max_length=255)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("End time is optional"),
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("e.g., Office, Client Site, Zoom Link"),
    )
    status = models.CharField(
        max_length=20,
        choices=CallMeetingStatusChoices.choices,
        default=CallMeetingStatusChoices.PLANNED,
    )
    description = models.TextField(blank=True)

    related_to_account = models.ForeignKey(
        'crm_entities.Account',
        related_name='meetings',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Related Account"),
    )
    related_to_contact = models.ForeignKey(
        'crm_entities.Contact',
        related_name='meetings',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Related Contact"),
    )
    related_to_lead = models.ForeignKey(
        'crm_entities.Lead',
        related_name='meetings',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Related Lead"),
    )
    related_to_deal = models.ForeignKey(
        'sales_pipeline.Deal',
        related_name='meetings',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Related Deal"),
    )

    created_by = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='created_meetings',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    assigned_to = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='assigned_meetings',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("User primarily responsible for this meeting"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Meeting")
        verbose_name_plural = _("Meetings")
        ordering = ['-start_time']

    def __str__(self):
        return self.subject