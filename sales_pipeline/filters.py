import django_filters
from django import forms
from django_filters import DateFromToRangeFilter

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field
from dal import autocomplete

from .models import Deal, Quote
from crm_entities.models import Account
from users.models import CustomUser


class DealFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Deal Name',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Name contains...',
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
    stage = django_filters.ChoiceFilter(
        choices=Deal.StageChoices.choices,
        label='Stage',
        empty_label='-- Stage --',
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
    close_date = DateFromToRangeFilter(
        field_name='close_date',
        label='Close Date Range',
        widget=django_filters.widgets.RangeWidget(
            attrs={
                'type': 'date',
                'class': 'form-control form-control-sm',
            }
        ),
    )

    class Meta:
        model = Deal
        fields = ['name', 'account', 'stage', 'assigned_to', 'close_date']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_tag = False
        self.helper.disable_csrf = True
        self.helper.layout = Layout(
            Row(
                Column(Field('name'), css_class='form-group col-md-6 mb-2'),
                Column(Field('account'), css_class='form-group col-md-6 mb-2'),
            ),
            Row(
                Column(Field('stage'), css_class='form-group col-md-4 mb-2'),
                Column(
                    Field('assigned_to'),
                    css_class='form-group col-md-4 mb-2',
                ),
                Column(
                    Field('close_date'),
                    css_class='form-group col-md-4 mb-2',
                ),
            ),
        )
        self.form.helper = self.helper


class QuoteFilter(django_filters.FilterSet):
    quote_id = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Quote ID',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'ID contains...',
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
    deal = django_filters.ModelChoiceFilter(
        queryset=Deal.objects.all(),
        label='Deal',
        widget=autocomplete.ModelSelect2(
            url='sales_pipeline:deal-autocomplete',
            attrs={
                'data-placeholder': 'Search deal...',
                'class': 'form-control form-control-sm',
            },
        ),
    )
    status = django_filters.ChoiceFilter(
        choices=Quote.StatusChoices.choices,
        label='Status',
        empty_label='-- Status --',
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
    presented_date = DateFromToRangeFilter(
        field_name='presented_date',
        label='Presented Date Range',
        widget=django_filters.widgets.RangeWidget(
            attrs={
                'type': 'date',
                'class': 'form-control form-control-sm',
            }
        ),
    )

    class Meta:
        model = Quote
        fields = [
            'quote_id',
            'account',
            'deal',
            'status',
            'assigned_to',
            'presented_date',
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
                    Field('quote_id'),
                    css_class='form-group col-md-6 mb-2',
                ),
                Column(Field('account'), css_class='form-group col-md-6 mb-2'),
            ),
            Row(
                Column(Field('deal'), css_class='form-group col-md-6 mb-2'),
                Column(
                    Field('assigned_to'),
                    css_class='form-group col-md-6 mb-2',
                ),
            ),
            Row(
                Column(Field('status'), css_class='form-group col-md-6 mb-2'),
                Column(
                    Field('presented_date'),
                    css_class='form-group col-md-6 mb-2',
                ),
            ),
        )
        self.form.helper = self.helper