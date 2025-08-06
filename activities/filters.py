import django_filters
from django import forms
from django_filters import DateFromToRangeFilter, DateTimeFromToRangeFilter

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column

from .models import (
    Task,
    Call,
    Meeting,
    TaskStatusChoices,
    TaskPriorityChoices,
    CallDirectionChoices,
    CallMeetingStatusChoices,
)
from users.models import CustomUser

# from crm_entities.models import Account, Contact, Lead
# from sales_pipeline.models import Deal


class TaskFilter(django_filters.FilterSet):
    subject = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Subject',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Subject contains...',
            }
        ),
    )
    status = django_filters.ChoiceFilter(
        choices=TaskStatusChoices.choices,
        label='Status',
        empty_label='-- Status --',
        widget=forms.Select(
            attrs={'class': 'form-select form-select-sm'}
        ),
    )
    priority = django_filters.ChoiceFilter(
        choices=TaskPriorityChoices.choices,
        label='Priority',
        empty_label='-- Priority --',
        widget=forms.Select(
            attrs={'class': 'form-select form-select-sm'}
        ),
    )
    due_date = DateFromToRangeFilter(
        field_name='due_date',
        label='Due Date Range',
        widget=django_filters.widgets.RangeWidget(
            attrs={
                'type': 'date',
                'class': 'form-control form-control-sm',
            }
        ),
    )
    assigned_to = django_filters.ModelChoiceFilter(
        queryset=CustomUser.objects.all().order_by('username'),
        label='Assigned To',
        empty_label='-- User --',
        widget=forms.Select(
            attrs={'class': 'form-select form-select-sm'}
        ),
    )

    class Meta:
        model = Task
        fields = ['subject', 'status', 'priority', 'due_date', 'assigned_to']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_show_labels = True
        self.helper.disable_csrf = True
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('subject', css_class='form-group col-md-6 mb-2'),
                Column('assigned_to', css_class='form-group col-md-6 mb-2'),
            ),
            Row(
                Column('status', css_class='form-group col-md-4 mb-2'),
                Column('priority', css_class='form-group col-md-4 mb-2'),
                Column('due_date', css_class='form-group col-md-4 mb-2'),
            ),
        )
        self.form.helper = self.helper


class CallFilter(django_filters.FilterSet):
    subject = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Subject',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Subject contains...',
            }
        ),
    )
    direction = django_filters.ChoiceFilter(
        choices=CallDirectionChoices.choices,
        label='Direction',
        empty_label='-- Direction --',
        widget=forms.Select(
            attrs={'class': 'form-select form-select-sm'}
        ),
    )
    status = django_filters.ChoiceFilter(
        choices=CallMeetingStatusChoices.choices,
        label='Status',
        empty_label='-- Status --',
        widget=forms.Select(
            attrs={'class': 'form-select form-select-sm'}
        ),
    )
    call_time = DateTimeFromToRangeFilter(
        field_name='call_time',
        label='Call Time Range',
        widget=django_filters.widgets.RangeWidget(
            attrs={
                'type': 'datetime-local',
                'class': 'form-control form-control-sm',
            }
        ),
    )
    assigned_to = django_filters.ModelChoiceFilter(
        queryset=CustomUser.objects.all().order_by('username'),
        label='Assigned To',
        empty_label='-- User --',
        widget=forms.Select(
            attrs={'class': 'form-select form-select-sm'}
        ),
    )

    class Meta:
        model = Call
        fields = ['subject', 'direction', 'status', 'call_time', 'assigned_to']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_show_labels = True
        self.helper.disable_csrf = True
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('subject', css_class='form-group col-md-6 mb-2'),
                Column('assigned_to', css_class='form-group col-md-6 mb-2'),
            ),
            Row(
                Column('direction', css_class='form-group col-md-4 mb-2'),
                Column('status', css_class='form-group col-md-4 mb-2'),
                Column('call_time', css_class='form-group col-md-4 mb-2'),
            ),
        )
        self.form.helper = self.helper


class MeetingFilter(django_filters.FilterSet):
    subject = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Subject',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Subject contains...',
            }
        ),
    )
    location = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Location',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Location contains...',
            }
        ),
    )
    status = django_filters.ChoiceFilter(
        choices=CallMeetingStatusChoices.choices,
        label='Status',
        empty_label='-- Status --',
        widget=forms.Select(
            attrs={'class': 'form-select form-select-sm'}
        ),
    )
    start_time = DateTimeFromToRangeFilter(
        field_name='start_time',
        label='Start Time Range',
        widget=django_filters.widgets.RangeWidget(
            attrs={
                'type': 'datetime-local',
                'class': 'form-control form-control-sm',
            }
        ),
    )
    assigned_to = django_filters.ModelChoiceFilter(
        queryset=CustomUser.objects.all().order_by('username'),
        label='Assigned To',
        empty_label='-- User --',
        widget=forms.Select(
            attrs={'class': 'form-select form-select-sm'}
        ),
    )

    class Meta:
        model = Meeting
        fields = ['subject', 'location', 'status', 'start_time', 'assigned_to']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_show_labels = True
        self.helper.disable_csrf = True
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('subject', css_class='form-group col-md-6 mb-2'),
                Column('location', css_class='form-group col-md-6 mb-2'),
            ),
            Row(
                Column('status', css_class='form-group col-md-4 mb-2'),
                Column('assigned_to', css_class='form-group col-md-4 mb-2'),
                Column('start_time', css_class='form-group col-md-4 mb-2'),
            ),
        )
        self.form.helper = self.helper