# sales_territories/admin.py
from django.contrib import admin
from .models import Territory

@admin.register(Territory)
class TerritoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'manager', 'description')
    search_fields = ('name', 'description', 'manager__username')
    autocomplete_fields = ['manager'] # Makes selecting manager easier if many users