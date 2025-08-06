import django
import django_filters
from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field
from dal import autocomplete

from .models import Account, Contact, Lead
from sales_territories.models import Territory
from users.models import CustomUser


class AccountFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Account Name',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Name contains...',
            }
        ),
    )
    industry = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Industry',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Industry contains...',
            }
        ),
    )
    status = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Status',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Status contains...',
            }
        ),
    )
    territory = django_filters.ModelChoiceFilter(
        queryset=Territory.objects.all().order_by('name'),
        label='Territory',
        empty_label='-- Territory --',
        widget=forms.Select(
            attrs={'class': 'form-select form-select-sm'}
        ),
    )
    assigned_to = django_filters.ModelChoiceFilter(
        queryset=CustomUser.objects.filter(is_active=True).order_by('username'),
        label='Assigned To',
        empty_label='-- User --',
        widget=forms.Select(
            attrs={'class': 'form-select form-select-sm'}
        ),
    )

    class Meta:
        model = Account
        fields = ['name', 'industry', 'status', 'territory', 'assigned_to']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_tag = False
        self.helper.disable_csrf = True
        self.helper.layout = Layout(
            Row(
                Column(Field('name'), css_class='form-group col-md-6 mb-2'),
                Column(Field('industry'), css_class='form-group col-md-6 mb-2'),
            ),
            Row(
                Column(Field('status'), css_class='form-group col-md-4 mb-2'),
                Column(Field('territory'), css_class='form-group col-md-4 mb-2'),
                Column(
                    Field('assigned_to'),
                    css_class='form-group col-md-4 mb-2',
                ),
            ),
        )
        self.form.helper = self.helper


class ContactFilter(django_filters.FilterSet):
    first_name = django_filters.CharFilter(
        lookup_expr='icontains',
        label='First Name',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'First Name contains...',
            }
        ),
    )
    last_name = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Last Name',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Last Name contains...',
            }
        ),
    )
    title = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Title',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Title contains...',
            }
        ),
    )
    department = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Department',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Department contains...',
            }
        ),
    )
    account = django_filters.ModelChoiceFilter(
        queryset=Account.objects.all(),
        label='Account',
        widget=autocomplete.ModelSelect2(
            url='crm_entities:account-autocomplete',
            attrs={
                'data-placeholder': 'Search Account...',
                'class': 'form-control form-control-sm',
            },
        ),
    )
    assigned_to = django_filters.ModelChoiceFilter(
        queryset=CustomUser.objects.filter(is_active=True).order_by('username'),
        label='Assigned To',
        empty_label='-- User --',
        widget=forms.Select(
            attrs={'class': 'form-select form-select-sm'}
        ),
    )

    class Meta:
        model = Contact
        fields = [
            'first_name',
            'last_name',
            'title',
            'department',
            'account',
            'assigned_to',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_tag = False
        self.helper.disable_csrf = True
        self.helper.layout = Layout(
            Row(
                Column(
                    Field('first_name'),
                    css_class='form-group col-md-6 mb-2',
                ),
                Column(
                    Field('last_name'),
                    css_class='form-group col-md-6 mb-2',
                ),
            ),
            Row(
                Column(Field('title'), css_class='form-group col-md-6 mb-2'),
                Column(
                    Field('department'),
                    css_class='form-group col-md-6 mb-2',
                ),
            ),
            Row(
                Column(Field('account'), css_class='form-group col-md-6 mb-2'),
                Column(
                    Field('assigned_to'),
                    css_class='form-group col-md-6 mb-2',
                ),
            ),
        )
        self.form.helper = self.helper


class LeadFilter(django_filters.FilterSet):
    first_name = django_filters.CharFilter(
        lookup_expr='icontains',
        label='First Name',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'First Name contains...',
            }
        ),
    )
    last_name = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Last Name',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Last Name contains...',
            }
        ),
    )
    company_name = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Company',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Company contains...',
            }
        ),
    )
    status = django_filters.ChoiceFilter(
        choices=Lead.StatusChoices.choices,
        label='Status',
        empty_label='-- Status --',
        widget=forms.Select(
            attrs={'class': 'form-select form-select-sm'}
        ),
    )
    source = django_filters.ChoiceFilter(
        choices=Lead.SourceChoices.choices,
        label='Source',
        empty_label='-- Source --',
        widget=forms.Select(
            attrs={'class': 'form-select form-select-sm'}
        ),
    )
    territory = django_filters.ModelChoiceFilter(
        queryset=Territory.objects.all().order_by('name'),
        label='Territory',
        empty_label='-- Territory --',
        widget=forms.Select(
            attrs={'class': 'form-select form-select-sm'}
        ),
    )
    assigned_to = django_filters.ModelChoiceFilter(
        queryset=CustomUser.objects.filter(is_active=True).order_by('username'),
        label='Assigned To',
        empty_label='-- User --',
        widget=forms.Select(
            attrs={'class': 'form-select form-select-sm'}
        ),
    )

    class Meta:
        model = Lead
        fields = [
            'first_name',
            'last_name',
            'company_name',
            'status',
            'source',
            'territory',
            'assigned_to',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_tag = False
        self.helper.disable_csrf = True
        self.helper.layout = Layout(
            Row(
                Column(
                    Field('first_name'),
                    css_class='form-group col-md-6 mb-2',
                ),
                Column(
                    Field('last_name'),
                    css_class='form-group col-md-6 mb-2',
                ),
            ),
            Row(
                Column(
                    Field('company_name'),
                    css_class='form-group col-md-6 mb-2',
                ),
                Column(
                    Field('assigned_to'),
                    css_class='form-group col-md-6 mb-2',
                ),
            ),
            Row(
                Column(Field('status'), css_class='form-group col-md-4 mb-2'),
                Column(Field('source'), css_class='form-group col-md-4 mb-2'),
                Column(
                    Field('territory'),
                    css_class='form-group col-md-4 mb-2',
                ),
            ),
        )
        self.form.helper = self.helper