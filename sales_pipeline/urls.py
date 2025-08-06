# sales_pipeline/urls.py
from django.urls import path
# Import all views from the current directory's views.py
from . import views
from .views import deal_export_view, quote_export_view
from .views import DealAutocomplete #QuoteAutocomplete

app_name = 'sales_pipeline' 

urlpatterns = [
    # Deal URLs
    path('deals/', views.DealListView.as_view(), name='deal-list'),
    path('deals/create/', views.DealCreateView.as_view(), name='deal-create'),
    path('deals/<int:pk>/', views.DealDetailView.as_view(), name='deal-detail'),
    path('deals/<int:pk>/update/', views.DealUpdateView.as_view(), name='deal-update'),
    path('deals/<int:pk>/delete/', views.DealDeleteView.as_view(), name='deal-delete'),
    path('deals/export/', deal_export_view, name='deal-export'), # Added export URL


    # --- Add Quote URLs below when you implement Quote Views ---
    path('quotes/', views.QuoteListView.as_view(), name='quote-list'),
    path('quotes/create/', views.QuoteCreateView.as_view(), name='quote-create'),
    path('quotes/<int:pk>/', views.QuoteDetailView.as_view(), name='quote-detail'),
    path('quotes/<int:pk>/update/', views.QuoteUpdateView.as_view(), name='quote-update'),
    path('quotes/<int:pk>/delete/', views.QuoteDeleteView.as_view(), name='quote-delete'),
    path('quotes/export/', quote_export_view, name='quote-export'), # Added export URL
    
    # --- Add Autocomplete URL ---
    path('deal-autocomplete/', DealAutocomplete.as_view(), name='deal-autocomplete'),
    #path('quote_autocomplete/',QuoteAutocomplete.as_view(), name='quote-autocomplete'),
    # --- End Autocomplete URL ---

]