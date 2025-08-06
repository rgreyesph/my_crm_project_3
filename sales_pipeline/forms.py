from django import forms

from dal import autocomplete
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field

from .models import Deal, Quote
from crm_entities.models import Account, Contact
from users.models import CustomUser


UserAutoCompleteWidget = autocomplete.ModelSelect2(
    url='users:user-autocomplete',
    attrs={'data-placeholder': 'Search User...'},
)
AccountAutoCompleteWidget = autocomplete.ModelSelect2(
    url='crm_entities:account-autocomplete',
    attrs={'data-placeholder': 'Search Account...'},
)
ContactAutoCompleteWidget = autocomplete.ModelSelect2(
    url='crm_entities:contact-autocomplete',
    attrs={'data-placeholder': 'Search Contact...'},
)
DealAutoCompleteWidget = autocomplete.ModelSelect2(
    url='sales_pipeline:deal-autocomplete',
    attrs={'data-placeholder': 'Search Deal...'},
)


class DealForm(forms.ModelForm):
    close_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control form-control-sm',
            }
        ),
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={'class': 'form-control form-control-sm'}
        ),
    )

    class Meta:
        model = Deal
        fields = [
            'name',
            'account',
            'primary_contact',
            'stage',
            'amount',
            'currency',
            'close_date',
            'description',
            'assigned_to',
        ]
        widgets = {
            'name': forms.TextInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            'description': forms.Textarea(attrs={'rows': 3}),
            'account': AccountAutoCompleteWidget,
            'primary_contact': ContactAutoCompleteWidget,
            'assigned_to': UserAutoCompleteWidget,
            'stage': forms.Select(
                attrs={'class': 'form-select form-select-sm'}
            ),
            'currency': forms.TextInput(
                attrs={'class': 'form-control form-control-sm'}
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
                Column(Field('account'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(
                    Field('primary_contact'),
                    css_class='col-md-6 mb-3',
                ),
                Column(Field('assigned_to'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(Field('stage'), css_class='col-md-12 mb-3'),
            ),
            Row(
                Column(Field('amount'), css_class='col-md-6 mb-3'),
                Column(Field('currency'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(Field('close_date'), css_class='col-md-6 mb-3'),
            ),
            Field('description'),
        )


class QuoteForm(forms.ModelForm):
    presented_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control form-control-sm',
            }
        ),
        required=False,
    )
    validity_days = forms.IntegerField(
        widget=forms.NumberInput(
            attrs={'class': 'form-control form-control-sm'}
        ),
        initial=30,
    )
    total_amount = forms.DecimalField(
        widget=forms.NumberInput(
            attrs={'class': 'form-control form-control-sm'}
        ),
        required=False,
    )

    class Meta:
        model = Quote
        fields = [
            'deal',
            'contact',
            'presented_date',
            'validity_days',
            'status',
            'total_amount',
            'notes',
            'assigned_to',
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'deal': DealAutoCompleteWidget,
            'contact': ContactAutoCompleteWidget,
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
        quote_id_display = None
        if self.instance and self.instance.pk and self.instance.quote_id:
            quote_id_display = Field('instance.quote_id', type='hidden')
        self.helper.layout = Layout(
            Row(
                Column(Field('deal'), css_class='col-md-6 mb-3'),
                Column(Field('contact'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(Field('status'), css_class='col-md-4 mb-3'),
                Column(
                    Field('presented_date'),
                    css_class='col-md-4 mb-3',
                ),
                Column(
                    Field('validity_days'),
                    css_class='col-md-4 mb-3',
                ),
            ),
            Row(
                Column(
                    Field('total_amount'),
                    css_class='col-md-6 mb-3',
                ),
                Column(Field('assigned_to'), css_class='col-md-6 mb-3'),
            ),
            Field('notes'),
        )