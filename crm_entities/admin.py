# crm_entities/admin.py
from django.contrib import admin
from .models import Account, Contact, Lead

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'website', 'status', 'territory', 'assigned_to', 'updated_at')
    list_filter = ('status', 'industry', 'territory', 'assigned_to')
    search_fields = ('name', 'website', 'phone_number', 'territory__name') # Account still has phone_number
    autocomplete_fields = ['territory', 'assigned_to']

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    # *** Ensure list_display uses correct fields ***
    list_display = (
        'full_name', 'account', 'title', 'department', 'email',
        'work_phone', # Use new field name
        'assigned_to', 'updated_at'
    )
    list_filter = ('account', 'assigned_to', 'account__territory', 'department')
    # *** Ensure search_fields uses correct fields ***
    search_fields = (
        'first_name', 'last_name', 'email', 'account__name', 'department',
        'work_phone', 'mobile_phone_1', 'mobile_phone_2' # Search new phone fields
    )
    autocomplete_fields = ['account', 'assigned_to']

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    # *** Ensure list_display uses correct fields ***
    list_display = (
        'full_name', 'company_name', 'status', 'department',
        'work_phone', # Use new field name
        'source', 'territory', 'assigned_to', 'updated_at'
    )
    list_filter = ('status', 'source', 'territory', 'assigned_to', 'department')
    # *** Ensure search_fields uses correct fields ***
    search_fields = (
        'first_name', 'last_name', 'email', 'company_name', 'department',
        'territory__name', 'work_phone', 'mobile_phone_1', 'mobile_phone_2' # Search new phone fields
    )
    autocomplete_fields = ['territory', 'assigned_to']