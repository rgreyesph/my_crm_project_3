# sales_performance/admin.py
from django.contrib import admin
from .models import SalesTarget

@admin.register(SalesTarget)
class SalesTargetAdmin(admin.ModelAdmin):
    list_display = ('user', 'target_amount', 'start_date', 'end_date', 'period_description')
    list_filter = ('user', 'start_date', 'end_date')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    list_per_page = 20
    autocomplete_fields = ['user'] # Use autocomplete if you set it up for Users