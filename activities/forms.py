# activities/forms.py (Corrected Version)

from django import forms

from dal import autocomplete
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field

from .models import Task, Call, Meeting
from crm_entities.models import Account, Contact, Lead
from sales_pipeline.models import Deal
from users.models import CustomUser


# --- Autocomplete Widgets (No changes here) ---
AccountAutoCompleteWidget = autocomplete.ModelSelect2(
    url='crm_entities:account-autocomplete',
    attrs={'data-placeholder': 'Search Account...'},
)
ContactAutoCompleteWidget = autocomplete.ModelSelect2(
    url='crm_entities:contact-autocomplete',
    attrs={'data-placeholder': 'Search Contact...'},
)
LeadAutoCompleteWidget = autocomplete.ModelSelect2(
    url='crm_entities:lead-autocomplete',
    attrs={'data-placeholder': 'Search Lead...'},
)
DealAutoCompleteWidget = autocomplete.ModelSelect2(
    url='sales_pipeline:deal-autocomplete',
    attrs={'data-placeholder': 'Search Deal...'},
)
UserAutoCompleteWidget = autocomplete.ModelSelect2(
    url='users:user-autocomplete',
    attrs={'data-placeholder': 'Search User...'},
)

# --- Input Widgets (No changes here) ---
DateTimeInputWidget = forms.DateTimeInput(
    attrs={
        'type': 'datetime-local',
        'class': 'form-control form-control-sm',
    }
)
DateInputWidget = forms.DateInput(
    attrs={
        'type': 'date',
        'class': 'form-control form-control-sm',
    }
)

# FIX: 1. Define a list of acceptable date/time formats
DATETIME_INPUT_FORMATS = [
    '%Y-%m-%dT%H:%M',  # Format from mobile browsers (e.g., 2025-06-21T09:30)
    '%Y-%m-%d %H:%M',  # Format from desktop browsers (e.g., 2025-06-21 09:30)
    '%Y-%m-%d %H:%M:%S',# Format with seconds
]


class TaskForm(forms.ModelForm):
    due_date = forms.DateField(widget=DateInputWidget, required=False)

    class Meta:
        model = Task
        fields = [
            'subject',
            'due_date',
            'status',
            'priority',
            'description',
            'related_to_account',
            'related_to_contact',
            'related_to_lead',
            'related_to_deal',
            'assigned_to',
        ]
        widgets = {
            'subject': forms.TextInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            'description': forms.Textarea(attrs={'rows': 3}),
            'related_to_account': AccountAutoCompleteWidget,
            'related_to_contact': ContactAutoCompleteWidget,
            'related_to_lead': LeadAutoCompleteWidget,
            'related_to_deal': DealAutoCompleteWidget,
            'assigned_to': UserAutoCompleteWidget,
            'status': forms.Select(
                attrs={'class': 'form-select form-select-sm'}
            ),
            'priority': forms.Select(
                attrs={'class': 'form-select form-select-sm'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field('subject'),
            Row(
                Column(Field('status'), css_class='col-md-4 mb-3'),
                Column(Field('priority'), css_class='col-md-4 mb-3'),
                Column(Field('due_date'), css_class='col-md-4 mb-3'),
            ),
            Row(
                Column(Field('assigned_to'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(
                    Field('related_to_account'),
                    css_class='col-md-6 mb-3',
                ),
                Column(
                    Field('related_to_contact'),
                    css_class='col-md-6 mb-3',
                ),
            ),
            Row(
                Column(Field('related_to_lead'), css_class='col-md-6 mb-3'),
                Column(Field('related_to_deal'), css_class='col-md-6 mb-3'),
            ),
            Field('description'),
        )


class CallForm(forms.ModelForm):
    # FIX: 2. Apply the input_formats fix to the call_time field
    call_time = forms.DateTimeField(
        widget=DateTimeInputWidget, 
        required=False, 
        input_formats=DATETIME_INPUT_FORMATS
    )

    class Meta:
        model = Call
        fields = [
            'subject',
            'call_time',
            'duration_minutes',
            'direction',
            'status',
            'notes',
            'related_to_account',
            'related_to_contact',
            'related_to_lead',
            'related_to_deal',
            'assigned_to',
        ]
        widgets = {
            'subject': forms.TextInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'related_to_account': AccountAutoCompleteWidget,
            'related_to_contact': ContactAutoCompleteWidget,
            'related_to_lead': LeadAutoCompleteWidget,
            'related_to_deal': DealAutoCompleteWidget,
            'assigned_to': UserAutoCompleteWidget,
            'direction': forms.Select(
                attrs={'class': 'form-select form-select-sm'}
            ),
            'status': forms.Select(
                attrs={'class': 'form-select form-select-sm'}
            ),
            'duration_minutes': forms.NumberInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field('subject'),
            Row(
                Column(Field('call_time'), css_class='col-md-4 mb-3'),
                Column(
                    Field('duration_minutes'),
                    css_class='col-md-2 mb-3',
                ),
                Column(Field('direction'), css_class='col-md-3 mb-3'),
                Column(Field('status'), css_class='col-md-3 mb-3'),
            ),
            Row(
                Column(Field('assigned_to'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(
                    Field('related_to_account'),
                    css_class='col-md-6 mb-3',
                ),
                Column(
                    Field('related_to_contact'),
                    css_class='col-md-6 mb-3',
                ),
            ),
            Row(
                Column(Field('related_to_lead'), css_class='col-md-6 mb-3'),
                Column(Field('related_to_deal'), css_class='col-md-6 mb-3'),
            ),
            Field('notes'),
        )


class MeetingForm(forms.ModelForm):
    # FIX: 3. Apply the input_formats fix to the start_time and end_time fields
    start_time = forms.DateTimeField(
        widget=DateTimeInputWidget, 
        required=False,
        input_formats=DATETIME_INPUT_FORMATS
    )
    end_time = forms.DateTimeField(
        widget=DateTimeInputWidget, 
        required=False,
        input_formats=DATETIME_INPUT_FORMATS
    )

    class Meta:
        model = Meeting
        fields = [
            'subject',
            'start_time',
            'end_time',
            'location',
            'status',
            'description',
            'related_to_account',
            'related_to_contact',
            'related_to_lead',
            'related_to_deal',
            'assigned_to',
        ]
        widgets = {
            'subject': forms.TextInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            'description': forms.Textarea(attrs={'rows': 3}),
            'location': forms.TextInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            'related_to_account': AccountAutoCompleteWidget,
            'related_to_contact': ContactAutoCompleteWidget,
            'related_to_lead': LeadAutoCompleteWidget,
            'related_to_deal': DealAutoCompleteWidget,
            'assigned_to': UserAutoCompleteWidget,
            'status': forms.Select(
                attrs={'class': 'form-select form-select-sm'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field('subject'),
            Row(
                Column(Field('start_time'), css_class='col-md-6 mb-3'),
                Column(Field('end_time'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(Field('location'), css_class='col-md-6 mb-3'),
                Column(Field('status'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(Field('assigned_to'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(
                    Field('related_to_account'),
                    css_class='col-md-6 mb-3',
                ),
                Column(
                    Field('related_to_contact'),
                    css_class='col-md-6 mb-3',
                ),
            ),
            Row(
                Column(Field('related_to_lead'), css_class='col-md-6 mb-3'),
                Column(Field('related_to_deal'), css_class='col-md-6 mb-3'),
            ),
            Field('description'),
        )