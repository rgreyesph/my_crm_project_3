# users/views.py
from dal import autocomplete
from django.db.models import Q
from .models import CustomUser # Your custom user model
from django.contrib.auth.mixins import LoginRequiredMixin

class UserAutocomplete(LoginRequiredMixin, autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Basic filtering: only active users
        qs = CustomUser.objects.filter(is_active=True)

        # Allow searching by username, first name, last name
        if self.q:
            qs = qs.filter(
                Q(username__icontains=self.q) |
                Q(first_name__icontains=self.q) |
                Q(last_name__icontains=self.q)
            )

        # Optional: Add permission filtering here if needed
        # For assigning tasks/records, maybe any active user is okay?
        # Or perhaps filter by role or territory depending on context? Keep simple for now.

        return qs.order_by('username')

    # Optional: Customize how the user is displayed in the dropdown
    # def get_result_label(self, item):
    #     return f"{item.get_full_name()} ({item.username})"