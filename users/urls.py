# users/urls.py
from django.urls import path
from .views import UserAutocomplete # Import the view

app_name = 'users'

urlpatterns = [
    path('user-autocomplete/', UserAutocomplete.as_view(), name='user-autocomplete'),
    # Add other user-related URLs here if needed later
]