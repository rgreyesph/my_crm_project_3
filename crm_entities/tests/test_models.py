from django.test import TestCase
from django.utils import timezone
from users.models import CustomUser
from sales_territories.models import Territory
from ..models import Account, Contact, Lead


def create_user(username, role=CustomUser.Roles.SALES, is_superuser=False):
    if is_superuser:
        return CustomUser.objects.create_superuser(
            username=username, password="password123", email=f"{username}@example.com", role=CustomUser.Roles.ADMIN
        )
    return CustomUser.objects.create_user(
        username=username, password="password123", role=role, email=f"{username}@example.com"
    )


class AccountModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user('account_user')
        cls.territory = Territory.objects.create(name="Test Territory")
        cls.account = Account.objects.create(
            name="Test Account", territory=cls.territory, assigned_to=cls.user
        )

    def test_account_creation(self):
        self.assertEqual(self.account.name, "Test Account")
        self.assertEqual(self.account.territory, self.territory)
        self.assertEqual(self.account.assigned_to, self.user)
        self.assertIsNotNone(self.account.created_at)
        self.assertIsNotNone(self.account.updated_at)

    def test_optional_fields_nullable(self):
        account = Account.objects.create(name="Minimal Account", assigned_to=self.user)
        self.assertIsNone(account.territory)

    def test_str_method(self):
        self.assertEqual(str(self.account), "Test Account")


class ContactModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user('contact_user')
        cls.account = Account.objects.create(name="Test Account", assigned_to=cls.user)
        cls.contact = Contact.objects.create(
            first_name="John", last_name="Doe", email="john.doe@example.com",
            account=cls.account, assigned_to=cls.user
        )

    def test_contact_creation(self):
        self.assertEqual(self.contact.first_name, "John")
        self.assertEqual(self.contact.last_name, "Doe")
        self.assertEqual(self.contact.email, "john.doe@example.com")
        self.assertEqual(self.contact.account, self.account)
        self.assertEqual(self.contact.assigned_to, self.user)
        self.assertIsNotNone(self.contact.created_at)
        self.assertIsNotNone(self.contact.updated_at)

    def test_optional_fields_nullable(self):
        contact = Contact.objects.create(last_name="Smith", assigned_to=self.user)
        self.assertEqual(contact.first_name, '')
        self.assertIsNone(contact.email)
        self.assertIsNone(contact.account)

    def test_str_method(self):
        self.assertEqual(str(self.contact), "John Doe")


class LeadModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user('lead_user')
        cls.territory = Territory.objects.create(name="Test Territory")
        cls.lead = Lead.objects.create(
            first_name="Jane", last_name="Smith", email="jane.smith@example.com",
            status='NEW', source='WEB', territory=cls.territory, assigned_to=cls.user
        )

    def test_lead_creation(self):
        self.assertEqual(self.lead.first_name, "Jane")
        self.assertEqual(self.lead.last_name, "Smith")
        self.assertEqual(self.lead.email, "jane.smith@example.com")
        self.assertEqual(self.lead.status, 'NEW')
        self.assertEqual(self.lead.source, 'WEB')
        self.assertEqual(self.lead.territory, self.territory)
        self.assertEqual(self.lead.assigned_to, self.user)
        self.assertIsNotNone(self.lead.created_at)
        self.assertIsNotNone(self.lead.updated_at)

    def test_optional_fields_nullable(self):
        lead = Lead.objects.create(last_name="Brown", assigned_to=self.user)
        self.assertEqual(lead.first_name, '')
        self.assertIsNone(lead.email)
        self.assertIsNone(lead.territory)
        self.assertEqual(lead.status, 'NEW')
        self.assertEqual(lead.source, '')

    def test_str_method(self):
        self.assertEqual(str(self.lead), "Jane Smith")