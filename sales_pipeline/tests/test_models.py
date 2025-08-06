# sales_pipeline/tests/test_models.py

from django.test import TestCase
from django.utils import timezone # Import timezone
from datetime import date, timedelta
import re

# --- Use Absolute Imports - Ensure ALL needed models are imported ---
from sales_pipeline.models import Quote, Deal # Models from this app
from crm_entities.models import Account # Import Account from its app
from users.models import CustomUser # Import User model
# --- End Imports ---

from django.core.exceptions import ValidationError
from ..models import Deal, Quote

class QuoteModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(username='quote_test', password='password123', email='quote@example.com')
        cls.account = Account.objects.create(name="Test Account", assigned_to=cls.user)
        cls.deal = Deal.objects.create(
            name="Test Deal", account=cls.account, stage='PROSPECTING', amount=1000,
            close_date=timezone.now().date(), assigned_to=cls.user
        )

    def test_invalid_total_amount(self):
        quote_data = {
            'quote_id': 'Q001',
            'deal': self.deal,
            'account': self.account,
            'total_amount': -50,
            'presented_date': timezone.now().date(),
            'status': 'DRAFT',
            'assigned_to': self.user
        }
        quote = Quote(**quote_data)
        quote.full_clean()  # Validate model
        quote.save()
        self.assertEqual(Quote.objects.count(), 1)  # No validation error

    def test_invalid_status(self):
        quote_data = {
            'quote_id': 'Q002',
            'deal': self.deal,
            'account': self.account,
            'total_amount': 500,
            'presented_date': timezone.now().date(),
            'status': 'INVALID',
            'assigned_to': self.user
        }
        quote = Quote(**quote_data)
        with self.assertRaises(ValidationError) as cm:
            quote.full_clean()
        self.assertIn('status', cm.exception.message_dict)

class DealModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(username='deal_test', password='password123', email='deal@example.com')
        cls.account = Account.objects.create(name="Test Account", assigned_to=cls.user)

    def test_invalid_amount(self):
        deal_data = {
            'name': 'Invalid Deal',
            'account': self.account,
            'stage': 'PROSPECTING',
            'amount': -100,
            'close_date': timezone.now().date(),
            'assigned_to': self.user
        }
        deal = Deal(**deal_data)
        deal.full_clean()  # Validate model
        deal.save()
        self.assertEqual(Deal.objects.count(), 1)  # No validation error

    def test_invalid_stage(self):
        deal_data = {
            'name': 'Invalid Deal',
            'account': self.account,
            'stage': 'INVALID',
            'amount': 1000,
            'close_date': timezone.now().date(),
            'assigned_to': self.user
        }
        deal = Deal(**deal_data)
        with self.assertRaises(ValidationError) as cm:
            deal.full_clean()
        self.assertIn('stage', cm.exception.message_dict)
    
    def test_invalid_close_date(self):
        deal_data = {
            'name': 'Invalid Deal',
            'account': self.account,
            'stage': 'PROSPECTING',
            'amount': 1000,
            'close_date': 'invalid_date',  # Invalid format
            'assigned_to': self.user
        }
        deal = Deal(**deal_data)
        with self.assertRaises(ValidationError) as cm:
            deal.full_clean()
        self.assertIn('close_date', cm.exception.message_dict)
        