from django import forms

from dal import autocomplete
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field

from .models import Account, Contact, Lead
from users.models import CustomUser
from sales_territories.models import Territory

from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

class AccountForm(forms.ModelForm):
    website = forms.CharField(required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'e.g., http://www.example.com'})
    ) # Changed widget

    class Meta:
        model = Account
        fields = [
            'name',
            'website',
            'phone_number',
            'billing_address',
            'shipping_address',
            'industry',
            'status',
            'assigned_to',
            'territory',
        ]
        widgets = {
            'billing_address': forms.Textarea(attrs={'rows': 2}),
            'shipping_address': forms.Textarea(attrs={'rows': 2}),
            'assigned_to': autocomplete.ModelSelect2(
                url='users:user-autocomplete',
                attrs={'data-placeholder': 'Search user...'},
            ),
            'territory': forms.Select(
                attrs={'class': 'form-select form-select-sm'},
            ),
            'status': forms.Select(
                attrs={'class': 'form-select form-select-sm'},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column(Field('name'), css_class='col-md-6 mb-3'),
                Column(Field('assigned_to'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(Field('website'), css_class='col-md-6 mb-3'),
                Column(Field('phone_number'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(Field('industry'), css_class='col-md-4 mb-3'),
                Column(Field('status'), css_class='col-md-4 mb-3'),
                Column(Field('territory'), css_class='col-md-4 mb-3'),
            ),
            Row(
                Column(Field('billing_address'), css_class='col-md-6 mb-3'),
                Column(Field('shipping_address'), css_class='col-md-6 mb-3'),
            ),
        )
    def clean_website(self):
        website = self.cleaned_data.get('website')
        if website:
            # Strip leading/trailing whitespace
            website = website.strip()
            if not website:
                # If only whitespace was entered, treat as empty
                return '' # Return empty string if model's field allows blank=True

            # Prepend http:// if no common scheme is present
            if not website.startswith(('http://', 'https://', 'ftp://', 'ftps://')):
                website = 'http://' + website

            # Validate the potentially modified URL
            validate = URLValidator() # schemes defaults to ['http', 'https', 'ftp', 'ftps']
            try:
                validate(website)
            except ValidationError:
                # Raise a user-friendly error
                raise ValidationError(
                    "Please enter a valid website URL (e.g., www.example.com or http://example.com)",
                    code='invalid_url'
                )
        # Return the cleaned URL or an empty string if input was blank/whitespace only
        return website or ''

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = [
            'account',
            'first_name',
            'last_name',
            'title',
            'department',
            'email',
            'work_phone',
            'mobile_phone_1',
            'mobile_phone_2',
            'notes',
            'assigned_to',
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'account': autocomplete.ModelSelect2(
                url='crm_entities:account-autocomplete',
                attrs={'data-placeholder': 'Search account...'},
            ),
            'assigned_to': autocomplete.ModelSelect2(
                url='users:user-autocomplete',
                attrs={'data-placeholder': 'Search user...'},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column(Field('account'), css_class='col-md-6 mb-3'),
                Column(Field('assigned_to'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(Field('first_name'), css_class='col-md-6 mb-3'),
                Column(Field('last_name'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(Field('title'), css_class='col-md-6 mb-3'),
                Column(Field('department'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(Field('email'), css_class='col-md-6 mb-3'),
                Column(Field('work_phone'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(Field('mobile_phone_1'), css_class='col-md-6 mb-3'),
                Column(Field('mobile_phone_2'), css_class='col-md-6 mb-3'),
            ),
            Field('notes'),
        )


class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = [
            'first_name',
            'last_name',
            'company_name',
            'title',
            'department',
            'email',
            'work_phone',
            'mobile_phone_1',
            'mobile_phone_2',
            'address',
            'notes',
            'status',
            'source',
            'assigned_to',
            'territory',
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
            'assigned_to': autocomplete.ModelSelect2(
                url='users:user-autocomplete',
                attrs={'data-placeholder': 'Search user...'},
            ),
            'territory': forms.Select(
                attrs={'class': 'form-select form-select-sm'},
            ),
            'status': forms.Select(
                attrs={'class': 'form-select form-select-sm'},
            ),
            'source': forms.Select(
                attrs={'class': 'form-select form-select-sm'},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column(Field('first_name'), css_class='col-md-6 mb-3'),
                Column(Field('last_name'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(Field('company_name'), css_class='col-md-6 mb-3'),
                Column(Field('assigned_to'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(Field('title'), css_class='col-md-6 mb-3'),
                Column(Field('department'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(Field('email'), css_class='col-md-6 mb-3'),
                Column(Field('work_phone'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(Field('mobile_phone_1'), css_class='col-md-6 mb-3'),
                Column(Field('mobile_phone_2'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(Field('status'), css_class='col-md-4 mb-3'),
                Column(Field('source'), css_class='col-md-4 mb-3'),
                Column(Field('territory'), css_class='col-md-4 mb-3'),
            ),
            Field('address'),
            Field('notes'),
        )
