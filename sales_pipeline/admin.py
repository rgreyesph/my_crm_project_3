# sales_pipeline/admin.py
from django.contrib import admin
# Import both models
from .models import Deal, Quote

@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = (
        'deal_id', 'name', 'account', 'stage',
        'probability', # Keep probability in list display
        'amount', 'currency', 'close_date', 'assigned_to', 'updated_at'
    )
    list_filter = ('stage', 'currency', 'assigned_to', 'account__territory')
    search_fields = ('deal_id', 'name', 'account__name', 'primary_contact__first_name', 'primary_contact__last_name')
    # *** Add 'probability' to readonly_fields ***
    readonly_fields = ('deal_id', 'created_at', 'updated_at', 'created_by', 'probability')
    autocomplete_fields = ['account', 'primary_contact', 'assigned_to']

@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    # Use updated field names and calculated property
    list_display = (
        'quote_id', 'account', 'deal', 'status', 'total_amount',
        'presented_date', # Use new field
        'validity_days',  # Use new field
        'expiry_date',    # Display calculated property
        'assigned_to', 'updated_at'
    )
    list_filter = ('status', 'assigned_to', 'account__territory', 'presented_date') # Filter by new date field
    search_fields = ('quote_id', 'account__name', 'deal__name', 'contact__first_name')
    autocomplete_fields = ['deal', 'contact', 'assigned_to']
    # Make calculated field and auto-fields read-only
    readonly_fields = ('created_at', 'updated_at', 'created_by',
        'expiry_date', 'quote_id', 'account')
