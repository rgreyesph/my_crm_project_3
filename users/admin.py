# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    # Add 'territory' to the list display
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'role', 'territory') # Added territory
    # Add 'territory' to the filter options
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'role', 'territory') # Added territory

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'role'),
        }),
        # Add the Territory fieldset (uncommented and adjusted)
        ('Territory Info', {'fields': ('territory',)}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    # Add territory to add_fieldsets as well
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('role', 'phone_number')}),
        # Add the Territory fieldset (uncommented and adjusted)
        ('Territory Info', {'fields': ('territory',)}),
    )
    # Add autocomplete for easier selection
    autocomplete_fields = ['territory']


admin.site.register(CustomUser, CustomUserAdmin)