# crm_entities/urls.py
from django.urls import path
from . import views # Import all views from the current directory
from .views import account_export_view
from .views import AccountAutocomplete, ContactAutocomplete, LeadAutocomplete


app_name = 'crm_entities'

urlpatterns = [
    # Account URLs
    path('accounts/', views.AccountListView.as_view(), name='account-list'),
    path('accounts/create/', views.AccountCreateView.as_view(), name='account-create'),
    path('accounts/<int:pk>/', views.AccountDetailView.as_view(), name='account-detail'),
    path('accounts/<int:pk>/update/', views.AccountUpdateView.as_view(), name='account-update'),
    path('accounts/<int:pk>/delete/', views.AccountDeleteView.as_view(), name='account-delete'),
    path('accounts/export/', account_export_view, name='account-export'),

    # Add Contact URLs here 
    path('contacts/', views.ContactListView.as_view(), name='contact-list'),
    path('contacts/create/', views.ContactCreateView.as_view(), name='contact-create'),
    path('contacts/<int:pk>/', views.ContactDetailView.as_view(), name='contact-detail'),
    path('contacts/<int:pk>/update/', views.ContactUpdateView.as_view(), name='contact-update'),
    path('contacts/<int:pk>/delete/', views.ContactDeleteView.as_view(), name='contact-delete'),
    path('contacts/export/', views.contact_export_view, name='contact-export'),
   

    # Add Lead URLs here
    path('leads/', views.LeadListView.as_view(), name='lead-list'),
    path('leads/create/', views.LeadCreateView.as_view(), name='lead-create'),
    path('leads/<int:pk>/', views.LeadDetailView.as_view(), name='lead-detail'),
    path('leads/<int:pk>/update/', views.LeadUpdateView.as_view(), name='lead-update'),
    path('leads/<int:pk>/delete/', views.LeadDeleteView.as_view(), name='lead-delete'),
    # Add this URL pattern for lead conversion
    path('leads/<int:pk>/convert/', views.LeadConvertView.as_view(), name='lead-convert'),
    path('leads/export/', views.lead_export_view, name='lead-export'),
    
    #Autocomplete URLs
    path('account-autocomplete/', AccountAutocomplete.as_view(), name='account-autocomplete'),
    path('contact-autocomplete/', ContactAutocomplete.as_view(), name='contact-autocomplete'),
    path('lead-autocomplete/', LeadAutocomplete.as_view(), name='lead-autocomplete'),
    # --- End Autocomplete URLs ---
    
]