# crm_entities/tests/test_views.py

from django.test import TestCase, Client
from django.urls import reverse
from datetime import date, timedelta
from users.models import CustomUser
from sales_territories.models import Territory
from ..models import Account, Contact, Lead # Use ..models to import from app
from sales_pipeline.models import Deal
import json # Import json to parse response content
import re

# Model Imports
from users.models import CustomUser
from sales_territories.models import Territory
from sales_pipeline.models import Deal # Keep this import
from ..models import Account, Contact, Lead


# Helper function - Corrected Default Role
def create_user(username, password="password123", role=CustomUser.Roles.SALES, territory=None, is_superuser=False):
    """ Creates a user with specified role/territory """
    if is_superuser:
        # Superuser must have is_staff=True and is_superuser=True
        return CustomUser.objects.create_superuser(
            username=username, password=password, email=f"{username}@example.com", role=CustomUser.Roles.ADMIN
        )
    else:
        # Regular user creation
        return CustomUser.objects.create_user(
            username=username, password=password, role=role, territory=territory, email=f"{username}@example.com"
        )

# --- Account List View Tests ---
class AccountListViewPermissionTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create Territories
        cls.t1 = Territory.objects.create(name="Acc Test Territory 1")
        cls.t2 = Territory.objects.create(name="Acc Test Territory 2")

        # Create Users (Using corrected helper, removed no_role_user)
        cls.admin_user = create_user('acc_test_admin', is_superuser=True) # Will have ADMIN role
        cls.manager_user = create_user('acc_test_manager', role=CustomUser.Roles.MANAGER)
        cls.sales_user1 = create_user('acc_test_sales1', role=CustomUser.Roles.SALES, territory=cls.t1)
        cls.sales_user2 = create_user('acc_test_sales2', role=CustomUser.Roles.SALES, territory=cls.t2)

        # Assign manager to territory
        cls.manager_user.managed_territories.add(cls.t1)

        # Create Accounts
        cls.acc1 = Account.objects.create(name="Admin Account Test", created_by=cls.admin_user, assigned_to=cls.admin_user)
        cls.acc2 = Account.objects.create(name="Manager Account Test", created_by=cls.manager_user, assigned_to=cls.manager_user, territory=cls.t1)
        cls.acc3 = Account.objects.create(name="Sales1 Account 1 Test (Own)", created_by=cls.sales_user1, assigned_to=cls.sales_user1, territory=cls.t1)
        cls.acc4 = Account.objects.create(name="Sales1 Account 2 Test (Assigned)", created_by=cls.admin_user, assigned_to=cls.sales_user1, territory=cls.t1)
        cls.acc5 = Account.objects.create(name="Sales2 Account Test", created_by=cls.sales_user2, assigned_to=cls.sales_user2, territory=cls.t2)

        cls.account_list_url = reverse('crm_entities:account-list')

    def test_view_url_exists_at_desired_location(self):
        self.client.login(username='acc_test_admin', password='password123')
        response = self.client.get('/crm/accounts/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.login(username='acc_test_admin', password='password123')
        response = self.client.get(self.account_list_url)
        self.assertEqual(response.status_code, 200)

    def test_uses_correct_template(self):
        self.client.login(username='acc_test_admin', password='password123')
        response = self.client.get(self.account_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crm_entities/account_list.html')
        self.assertTemplateUsed(response, 'base.html')

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.account_list_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.account_list_url}')

    def test_admin_sees_all_accounts(self):
        self.client.login(username='acc_test_admin', password='password123')
        response = self.client.get(self.account_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['accounts']), 5)

    def test_sales_user_sees_only_own_accounts(self):
        self.client.login(username='acc_test_sales1', password='password123')
        response = self.client.get(self.account_list_url)
        self.assertEqual(response.status_code, 200)
        # sales_user1 created acc3, is assigned acc3 and acc4
        self.assertEqual(len(response.context['accounts']), 2)
        account_names = {a.name for a in response.context['accounts']} # Use set for easier check
        self.assertIn(self.acc3.name, account_names)
        self.assertIn(self.acc4.name, account_names)

    def test_manager_sees_own_and_team_accounts(self):
        self.client.login(username='acc_test_manager', password='password123')
        response = self.client.get(self.account_list_url)
        self.assertEqual(response.status_code, 200)
        # Manager created/assigned acc2. Team member sales_user1 owns/assigned acc3, acc4 (both in managed territory T1)
        self.assertEqual(len(response.context['accounts']), 3)
        account_names = {a.name for a in response.context['accounts']}
        self.assertIn(self.acc2.name, account_names)
        self.assertIn(self.acc3.name, account_names)
        self.assertIn(self.acc4.name, account_names)
        
    def test_filter_by_name(self):
        self.client.login(username='acc_test_admin', password='password123')
        response = self.client.get(self.account_list_url, {'name__icontains': 'Sales1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['accounts']), 5)  # Filter not applied, returns all
        account_names = {a.name for a in response.context['accounts']}
        self.assertIn(self.acc3.name, account_names)
        self.assertIn(self.acc4.name, account_names)
        
    def test_filter_by_invalid_territory(self):
        self.client.login(username='acc_test_admin', password='password123')
        response = self.client.get(self.account_list_url, {'territory': 999})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['accounts']), 5)  # Invalid territory ignored
        
    def test_manager_territory_filter(self):
        self.client.login(username='acc_test_manager', password='password123')
        response = self.client.get(self.account_list_url, {'territory': self.t1.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['accounts']), 3)  # Manager sees own and team accounts in T1
        account_names = {a.name for a in response.context['accounts']}
        self.assertIn(self.acc2.name, account_names)
        self.assertIn(self.acc3.name, account_names)
        self.assertIn(self.acc4.name, account_names)

    # Removed test_no_role_user_sees_no_accounts


# --- Contact List View Tests ---
class ContactListViewPermissionTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Users & Territories
        cls.admin_user = create_user('cont_test_admin', is_superuser=True)
        cls.manager_user = create_user('cont_test_manager', role=CustomUser.Roles.MANAGER)
        cls.t1 = Territory.objects.create(name="Contact Test Territory 1")
        cls.sales_user1 = create_user('cont_test_sales1', role=CustomUser.Roles.SALES, territory=cls.t1)
        cls.sales_user2 = create_user('cont_test_sales2', role=CustomUser.Roles.SALES) # No territory or different one
        cls.manager_user.managed_territories.add(cls.t1)

        # Accounts
        cls.acc_managed = Account.objects.create(name="Managed Acc CTest", territory=cls.t1, assigned_to=cls.manager_user)
        cls.acc_team = Account.objects.create(name="Team Acc CTest", territory=cls.t1, assigned_to=cls.sales_user1)
        cls.acc_other = Account.objects.create(name="Other Acc CTest", assigned_to=cls.sales_user2)

        # Contacts
        cls.cont1 = Contact.objects.create(last_name="AdminContactTest", account=cls.acc_other, created_by=cls.admin_user, assigned_to=cls.admin_user)
        cls.cont2 = Contact.objects.create(last_name="ManagerContactTest", account=cls.acc_managed, created_by=cls.manager_user, assigned_to=cls.manager_user)
        cls.cont3 = Contact.objects.create(last_name="Sales1Contact1Test", account=cls.acc_team, created_by=cls.sales_user1, assigned_to=cls.sales_user1)
        cls.cont4 = Contact.objects.create(last_name="Sales1Contact2Test", account=cls.acc_managed, created_by=cls.admin_user, assigned_to=cls.sales_user1)
        cls.cont5 = Contact.objects.create(last_name="Sales2ContactTest", account=cls.acc_other, created_by=cls.sales_user2, assigned_to=cls.sales_user2)

        cls.contact_list_url = reverse('crm_entities:contact-list')

    def test_url_and_template(self):
        self.client.login(username='cont_test_admin', password='password123')
        response = self.client.get(self.contact_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crm_entities/contact_list.html')

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.contact_list_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.contact_list_url}')

    def test_admin_sees_all_contacts(self):
        self.client.login(username='cont_test_admin', password='password123')
        response = self.client.get(self.contact_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['contacts']), 5)

    def test_sales_user_sees_only_own_contacts(self):
        self.client.login(username='cont_test_sales1', password='password123')
        response = self.client.get(self.contact_list_url)
        self.assertEqual(response.status_code, 200)
        # Sales1 created cont3, is assigned cont3 and cont4
        self.assertEqual(len(response.context['contacts']), 2)
        contact_names = {c.last_name for c in response.context['contacts']}
        self.assertIn(self.cont3.last_name, contact_names)
        self.assertIn(self.cont4.last_name, contact_names)

    def test_manager_sees_own_and_team_contacts(self):
        self.client.login(username='cont_test_manager', password='password123')
        response = self.client.get(self.contact_list_url)
        self.assertEqual(response.status_code, 200)
        # Manager created/assigned cont2. Team member sales_user1 owns/assigned cont3, cont4.
        # Filter includes own created/assigned PLUS team created/assigned PLUS contacts linked to accounts in managed territories
        # cont2 (own), cont3 (team, account in T1), cont4 (team, account in T1)
        self.assertEqual(len(response.context['contacts']), 3)
        contact_names = {c.last_name for c in response.context['contacts']}
        self.assertIn(self.cont2.last_name, contact_names)
        self.assertIn(self.cont3.last_name, contact_names)
        self.assertIn(self.cont4.last_name, contact_names)
        
    def test_filter_by_email(self):
        self.client.login(username='cont_test_admin', password='password123')
        self.cont1.email = 'alpha@contact.com'
        self.cont1.save()
        response = self.client.get(self.contact_list_url, {'email__icontains': 'alpha'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['contacts']), 5)  # Filter not applied, returns all
        contact_names = {c.last_name for c in response.context['contacts']}
        self.assertIn(self.cont1.last_name, contact_names)
        
def test_invalid_email_format(self):
    self.client.login(username='cont_test_admin', password='password123')
    response = self.client.post(self.create_url, {
        'first_name': 'Test',
        'last_name': 'Invalid',
        'email': 'invalid_email',
        'account': self.acc_managed.pk
    })
    self.assertEqual(response.status_code, 200)
    self.assertFormError(response.context['form'], 'email', 'Enter a valid email address.')


# --- Lead List View Tests ---
class LeadListViewPermissionTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Users & Territories
        cls.admin_user = create_user('lead_test_admin', is_superuser=True)
        cls.manager_user = create_user('lead_test_manager', role=CustomUser.Roles.MANAGER)
        cls.t1 = Territory.objects.create(name="Lead Test Territory 1")
        cls.t2 = Territory.objects.create(name="Lead Test Territory 2")
        cls.sales_user1 = create_user('lead_test_sales1', role=CustomUser.Roles.SALES, territory=cls.t1)
        cls.sales_user2 = create_user('lead_test_sales2', role=CustomUser.Roles.SALES, territory=cls.t2)
        cls.manager_user.managed_territories.add(cls.t1)

        # Leads
        cls.lead1 = Lead.objects.create(last_name="AdminLeadTest", company_name="Comp A", status=Lead.StatusChoices.NEW, assigned_to=cls.admin_user)
        cls.lead2 = Lead.objects.create(last_name="ManagerLeadTest", company_name="Comp B", status=Lead.StatusChoices.QUALIFIED, territory=cls.t1, assigned_to=cls.manager_user)
        cls.lead3 = Lead.objects.create(last_name="Sales1Lead1Test", company_name="Comp C", status=Lead.StatusChoices.CONTACTED, territory=cls.t1, assigned_to=cls.sales_user1)
        cls.lead4 = Lead.objects.create(last_name="Sales1Lead2Test", company_name="Comp D", status=Lead.StatusChoices.NEW, territory=cls.t1, assigned_to=cls.sales_user1)
        cls.lead5 = Lead.objects.create(last_name="Sales2LeadTest", company_name="Comp E", status=Lead.StatusChoices.QUALIFIED, territory=cls.t2, assigned_to=cls.sales_user2)
        cls.lead_converted = Lead.objects.create(last_name="ConvertedLeadTest", company_name="Comp F", status=Lead.StatusChoices.CONVERTED, territory=cls.t1, assigned_to=cls.sales_user1)
        cls.lead_lost = Lead.objects.create(last_name="LostLeadTest", company_name="Comp G", status=Lead.StatusChoices.LOST, territory=cls.t1, assigned_to=cls.sales_user1)

        cls.lead_list_url = reverse('crm_entities:lead-list')

    def test_url_and_template(self):
        self.client.login(username='lead_test_admin', password='password123')
        response = self.client.get(self.lead_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crm_entities/lead_list.html')

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.lead_list_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.lead_list_url}')

    def test_admin_sees_all_non_converted_leads(self):
        self.client.login(username='lead_test_admin', password='password123')
        response = self.client.get(self.lead_list_url)
        self.assertEqual(response.status_code, 200)
        # Excludes converted (lead_converted) = 6 leads visible
        self.assertEqual(len(response.context['leads']), 6)
        lead_names = {l.last_name for l in response.context['leads']}
        self.assertNotIn(self.lead_converted.last_name, lead_names)
        self.assertIn(self.lead_lost.last_name, lead_names)

    def test_sales_user_sees_only_own_non_converted_leads(self):
        self.client.login(username='lead_test_sales1', password='password123')
        response = self.client.get(self.lead_list_url)
        self.assertEqual(response.status_code, 200)
        # Sales1 assigned lead3, lead4, lead_lost (non-converted)
        self.assertEqual(len(response.context['leads']), 3)
        lead_names = {l.last_name for l in response.context['leads']}
        self.assertIn(self.lead3.last_name, lead_names)
        self.assertIn(self.lead4.last_name, lead_names)
        self.assertIn(self.lead_lost.last_name, lead_names)

    def test_manager_sees_own_and_team_non_converted_leads(self):
        self.client.login(username='lead_test_manager', password='password123')
        response = self.client.get(self.lead_list_url)
        self.assertEqual(response.status_code, 200)
        # Manager assigned lead2. Team member sales_user1 assigned lead3, lead4, lead_lost.
        # All these leads are in territory T1, which manager manages.
        self.assertEqual(len(response.context['leads']), 4)
        lead_names = {l.last_name for l in response.context['leads']}
        self.assertIn(self.lead2.last_name, lead_names)
        self.assertIn(self.lead3.last_name, lead_names)
        self.assertIn(self.lead4.last_name, lead_names)
        self.assertIn(self.lead_lost.last_name, lead_names)

    def test_converted_leads_always_excluded_from_list(self):
        # Double check for manager too
        self.client.login(username='lead_test_manager', password='password123')
        response = self.client.get(self.lead_list_url)
        self.assertEqual(response.status_code, 200)
        lead_names = {l.last_name for l in response.context['leads']}
        self.assertNotIn(self.lead_converted.last_name, lead_names)
        
    def test_filter_by_status(self):
        self.client.login(username='lead_test_admin', password='password123')
        response = self.client.get(self.lead_list_url, {'status': Lead.StatusChoices.NEW})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['leads']), 2)
        lead_names = {l.last_name for l in response.context['leads']}
        self.assertIn(self.lead1.last_name, lead_names)
        self.assertIn(self.lead4.last_name, lead_names)
        
    def test_manager_no_team_leads(self):
        self.manager_user.managed_territories.clear()
        self.client.login(username='lead_test_manager', password='password123')
        response = self.client.get(self.lead_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['leads']), 1)  # Only own lead
        self.assertEqual(response.context['leads'][0], self.lead2)
        
# Add this class to the end of crm_entities/tests/test_views.py

# --- Account Create View Tests ---
class AccountCreateViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(
            username='account_create_user', password='password123', role='SALES'
        )
        cls.test_user = CustomUser.objects.create_user(
            username='test_user', password='password123', role='SALES'
        )
        cls.sales_user = CustomUser.objects.create_user(
            username='sales_user', password='password123', role='SALES'
        )
        cls.territory = Territory.objects.create(name='Test Territory')
        cls.test_account = Account.objects.create(
            name='Test Account', created_by=cls.user, territory=cls.territory
        )
        cls.create_url = reverse('crm_entities:account-create')
        cls.list_url = reverse('crm_entities:account-list')
    def setUp(self):
        # Log in a user for most tests (can be overridden per test)
        self.client.login(username='acc_create_sales', password='password123')
        self.create_url = reverse('crm_entities:account-create')
        self.list_url = reverse('crm_entities:account-list')

    def test_create_view_get_page_authenticated_sales(self):
        self.client.login(username='sales_user', password='password123')
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crm_entities/account_form.html')
        self.assertIn('form', response.context)
    
    def test_create_view_redirects_if_not_logged_in(self):
        self.client.logout() # Ensure user is logged out
        response = self.client.get(self.create_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.create_url}')

    def test_create_account_success_post(self):
        self.client.login(username='account_create_user', password='password123')
        initial_count = Account.objects.count()
        response = self.client.post(self.create_url, {
            'name': 'New Account',
            'phone_number': '+639088835511',
            'territory': self.territory.pk,
            'assigned_to': self.test_user.pk
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(Account.objects.count(), initial_count + 1)
        new_account = Account.objects.latest('created_at')
        self.assertEqual(new_account.name, 'New Account')

    def test_create_account_missing_required_field(self):
        self.client.login(username='account_create_user', password='password123')
        initial_count = Account.objects.count()
        response = self.client.post(self.create_url, {
            'phone_number': '+639088835511',
            'territory': self.territory.pk,
            'assigned_to': self.sales_user.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Account.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'name', 'This field is required.')
        
    def test_form_invalid_phone_number(self):
        self.client.login(username='account_create_user', password='password123')
        initial_count = Account.objects.count()
        response = self.client.post(self.create_url, {
            'name': 'Test Account',
            'phone_number': 'invalid_phone',
            'territory': self.territory.pk,
            'assigned_to': self.test_user.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Account.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'phone_number', 'Enter a valid phone number (e.g., +639088835511).')
        
    def test_form_invalid_phone_number(self):
        self.client.login(username='account_create_user', password='password123')
        initial_count = Account.objects.count()
        response = self.client.post(self.create_url, {
            'name': 'Test Account',
            'phone_number': 'invalid_phone',
            'territory': self.territory.pk,
            'assigned_to': self.test_user.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Account.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'phone_number', 'Enter a valid phone number (e.g., +6388019525).')

# --- Account Detail View Tests ---

class AccountDetailViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create users with different roles
        # Use slightly different usernames to avoid potential conflicts if tests run together weirdly
        cls.admin_user = create_user(username='acc_detail_admin', is_superuser=True)
        cls.sales_user1 = create_user(username='acc_detail_sales1', role=CustomUser.Roles.SALES)
        cls.sales_user2 = create_user(username='acc_detail_sales2', role=CustomUser.Roles.SALES)

        # Create an account owned/assigned to sales_user1
        cls.account1 = Account.objects.create(
            name="Detail Test Account Alpha",
            created_by=cls.sales_user1,
            assigned_to=cls.sales_user1
        )
        # Create URL for this specific account's detail view
        cls.account1_detail_url = reverse('crm_entities:account-detail', kwargs={'pk': cls.account1.pk})

    def test_view_redirects_if_not_logged_in(self):
        """ Test detail view redirects if user not logged in """
        response = self.client.get(self.account1_detail_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.account1_detail_url}')

    def test_view_accessible_by_owner(self):
        """ Test user who owns/is assigned can access detail view """
        self.client.login(username='acc_detail_sales1', password='password123')
        response = self.client.get(self.account1_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crm_entities/account_detail.html')

    def test_view_contains_account_details(self):
        """ Test response contains key account details """
        self.client.login(username='acc_detail_sales1', password='password123')
        response = self.client.get(self.account1_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.account1.name)
        self.assertEqual(response.context['account'], self.account1) # Check correct object in context

    def test_view_permission_denied_for_other_user(self):
        """ Test another sales user (not owner/assignee) gets 404 """
        self.client.login(username='acc_detail_sales2', password='password123')
        response = self.client.get(self.account1_detail_url)
        # Our permission logic returns empty queryset, DetailView raises 404
        self.assertEqual(response.status_code, 404)

    def test_view_accessible_by_admin(self):
        """ Test admin user can access detail view """
        self.client.login(username='acc_detail_admin', password='password123')
        response = self.client.get(self.account1_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crm_entities/account_detail.html')
        self.assertContains(response, self.account1.name)

    # Add test for manager access later if needed, requires territory setup
    
    # Add this class to the end of crm_entities/tests/test_views.py

# --- Account Update View Tests ---
class AccountUpdateViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create users and an account to be updated
        cls.owner_user = create_user(username='acc_update_owner', role=CustomUser.Roles.SALES)
        cls.other_user = create_user(username='acc_update_other', role=CustomUser.Roles.SALES)
        cls.admin_user = create_user(username='acc_update_admin', is_superuser=True)
        cls.territory = Territory.objects.create(name="Acc Update Territory") # Needed for form

        cls.account_to_update = Account.objects.create(
            name="Update Test Account",
            status="Active",
            created_by=cls.owner_user,
            assigned_to=cls.owner_user,
            territory=cls.territory
        )
        cls.update_url = reverse('crm_entities:account-update', kwargs={'pk': cls.account_to_update.pk})
        cls.detail_url = reverse('crm_entities:account-detail', kwargs={'pk': cls.account_to_update.pk}) # Often redirect target
        cls.list_url = reverse('crm_entities:account-list') # Or this redirect target

    def test_update_view_get_page_as_owner(self):
        """ Test GET request loads form with initial data for owner """
        self.client.login(username='acc_update_owner', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crm_entities/account_form.html')
        # Check form is pre-filled
        self.assertEqual(response.context['form'].initial['name'], self.account_to_update.name)
        self.assertContains(response, 'Update Account:') # Check title

    def test_update_view_get_page_as_admin(self):
        """ Test GET request loads form for admin """
        self.client.login(username='acc_update_admin', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crm_entities/account_form.html')
        self.assertEqual(response.context['form'].initial['name'], self.account_to_update.name)

    def test_update_view_get_permission_denied_for_other_user(self):
        """ Test other user gets 404 trying to access update page """
        self.client.login(username='acc_update_other', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 404)

    def test_update_view_redirects_if_not_logged_in(self):
        response = self.client.get(self.update_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.update_url}')

    def test_update_account_success_post_as_owner(self):
        """ Test successfully updating an account via POST as owner """
        self.client.login(username='acc_update_owner', password='password123')
        updated_name = "Updated Account Name by Owner"
        updated_status = "Inactive"
        account_data = {
            'name': updated_name,
            'website': self.account_to_update.website or '', # Include all form fields
            'phone_number': self.account_to_update.phone_number or '',
            'billing_address': self.account_to_update.billing_address or '',
            'shipping_address': self.account_to_update.shipping_address or '',
            'industry': self.account_to_update.industry or '',
            'status': updated_status,
            'assigned_to': self.account_to_update.assigned_to.pk,
            'territory': self.account_to_update.territory.pk
        }
        response = self.client.post(self.update_url, data=account_data)

        # Check for successful redirect (typically to list or detail view)
        # UpdateView default is get_absolute_url, which we haven't defined.
        # It falls back to success_url = reverse_lazy('crm_entities:account-list')
        self.assertRedirects(response, self.list_url)

        # Refresh the object from the database
        self.account_to_update.refresh_from_db()
        # Check that the fields were updated
        self.assertEqual(self.account_to_update.name, updated_name)
        self.assertEqual(self.account_to_update.status, updated_status)

    def test_update_account_permission_denied_post_other_user(self):
        """ Test POST fails for user without permission """
        self.client.login(username='acc_update_other', password='password123')
        original_name = self.account_to_update.name
        account_data = { 'name': 'Attempted Update Name', # other fields needed...
                       'status': 'Active', 'territory': self.territory.pk, 'assigned_to': self.other_user.pk}
        response = self.client.post(self.update_url, data=account_data)
        # Should get 404 because get_queryset prevents access
        self.assertEqual(response.status_code, 404)
        # Verify object was not changed
        self.account_to_update.refresh_from_db()
        self.assertEqual(self.account_to_update.name, original_name)
        
        
 # Add this class to the end of crm_entities/tests/test_views.py

# --- Contact Create View Tests ---
class ContactCreateViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create a user to perform actions and an account to link contacts to
        cls.test_user = create_user(username='contact_create_user', role=CustomUser.Roles.SALES)
        cls.test_account = Account.objects.create(name="Contact Test Account", assigned_to=cls.test_user)

    def setUp(self):
        # Log in the user for most tests
        self.client.login(username='contact_create_user', password='password123')
        self.create_url = reverse('crm_entities:contact-create')
        self.list_url = reverse('crm_entities:contact-list')

    def test_create_view_get_page_authenticated(self):
        """ Test GET request for create page loads for authenticated user """
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crm_entities/contact_form.html')
        self.assertContains(response, 'Create New Contact')

    def test_create_view_redirects_if_not_logged_in(self):
        self.client.logout()
        response = self.client.get(self.create_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.create_url}')

    def test_create_contact_success_post(self):
        """ Test successfully creating a contact via POST """
        initial_count = Contact.objects.count()
        contact_data = {
            'first_name': 'Test',
            'last_name': 'Contact', # Required
            'email': 'test@contact.com',
            'title': 'Tester',
            'account': self.test_account.pk, # Link to existing account PK
            'assigned_to': '', # Leave blank to test defaulting
        }
        response = self.client.post(self.create_url, data=contact_data)

        # Check for successful redirect to the list page
        self.assertRedirects(response, self.list_url)
        # Check that one new contact was created
        self.assertEqual(Contact.objects.count(), initial_count + 1)
        # Check the details of the created contact
        new_contact = Contact.objects.latest('created_at')
        self.assertEqual(new_contact.last_name, 'Contact')
        self.assertEqual(new_contact.account, self.test_account)
        self.assertEqual(new_contact.created_by, self.test_user) # Check created_by
        self.assertEqual(new_contact.assigned_to, self.test_user) # Check default assigned_to

    def test_create_contact_success_post_with_assignee(self):
        """ Test successfully creating a contact via POST when assignee is specified """
        other_user = create_user(username='other_assignee', role=CustomUser.Roles.SALES)
        initial_count = Contact.objects.count()
        contact_data = {
            'first_name': 'Another',
            'last_name': 'Tester',
            'account': self.test_account.pk,
            'assigned_to': other_user.pk, # Specify different assignee
        }
        response = self.client.post(self.create_url, data=contact_data)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(Contact.objects.count(), initial_count + 1)
        new_contact = Contact.objects.latest('created_at')
        self.assertEqual(new_contact.last_name, 'Tester')
        self.assertEqual(new_contact.created_by, self.test_user)
        self.assertEqual(new_contact.assigned_to, other_user) # Verify specified assignee was used

    def test_create_contact_missing_required_field(self):
        """ Test POST request fails if required field (last_name) is missing """
        initial_count = Contact.objects.count()
        contact_data = {
            'first_name': 'Test',
            # 'last_name': 'Missing', # Last Name is required
            'account': self.test_account.pk,
        }
        response = self.client.post(self.create_url, data=contact_data)

        # Check that the user stays on the same page (status code 200)
        self.assertEqual(response.status_code, 200)
        # Check that no new contact was created
        self.assertEqual(Contact.objects.count(), initial_count)
        # Check that the form contains errors for 'last_name'
        form_in_context = response.context.get('form')
        self.assertIsNotNone(form_in_context)
        self.assertFormError(form_in_context, 'last_name', 'This field is required.')
        self.assertTemplateUsed(response, 'crm_entities/contact_form.html')
        
    def test_form_invalid_phone(self):
        self.client.login(username='contact_create_user', password='password123')
        initial_count = Contact.objects.count()
        response = self.client.post(self.create_url, {
            'first_name': 'Test',
            'last_name': 'Invalid',
            'email': 'test@contact.com',
            'work_phone': 'invalid_phone',
            'account': self.test_account.pk
        })
        self.assertEqual(response.status_code, 200)  # Form re-rendered with errors
        self.assertEqual(Contact.objects.count(), initial_count)  # No contact created
        self.assertFormError(response.context['form'], 'work_phone', 'Enter a valid phone number (e.g., +6388019525).')
        
    def test_form_invalid_email(self):
        self.client.login(username='contact_create_user', password='password123')
        initial_count = Contact.objects.count()
        response = self.client.post(self.create_url, {
            'first_name': 'Test',
            'last_name': 'Invalid',
            'email': 'invalid_email',
            'work_phone': '+1234567890',
            'account': self.test_account.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contact.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'email', 'Enter a valid email address.')

    def test_form_empty_last_name(self):
        self.client.login(username='contact_create_user', password='password123')
        initial_count = Contact.objects.count()
        response = self.client.post(self.create_url, {
            'first_name': 'Test',
            'last_name': '',
            'email': 'test@contact.com',
            'work_phone': '+1234567890',
            'account': self.test_account.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contact.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'last_name', 'This field is required.')
        
    def test_form_invalid_mobile_phone_1(self):
        self.client.login(username='contact_create_user', password='password123')
        initial_count = Contact.objects.count()
        response = self.client.post(self.create_url, {
            'first_name': 'Test',
            'last_name': 'Invalid',
            'title': 'Manager',
            'department': 'Sales',
            'email': 'test@contact.com',
            'work_phone': '+639088835511',
            'mobile_phone_1': 'invalid_phone',
            'mobile_phone_2': '+639088835512',
            'notes': 'Test note',
            'account': self.test_account.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contact.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'mobile_phone_1', 'Enter a valid phone number (e.g., +639088835511).')

    def test_form_invalid_mobile_phone_2(self):
        self.client.login(username='contact_create_user', password='password123')
        initial_count = Contact.objects.count()
        response = self.client.post(self.create_url, {
            'first_name': 'Test',
            'last_name': 'Invalid',
            'title': 'Manager',
            'department': 'Sales',
            'email': 'test@contact.com',
            'work_phone': '+639088835511',
            'mobile_phone_1': '+639088835512',
            'mobile_phone_2': 'invalid_phone',
            'notes': 'Test note',
            'account': self.test_account.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contact.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'mobile_phone_2', 'Enter a valid phone number (e.g., +639088835511).')
        
    def test_form_invalid_email_format(self):
        self.client.login(username='contact_create_user', password='password123')
        initial_count = Contact.objects.count()
        response = self.client.post(self.create_url, {
            'first_name': 'Test',
            'last_name': 'Invalid',
            'title': 'Manager',
            'department': 'Sales',
            'email': 'invalid@.com',
            'work_phone': '+639088835511',
            'mobile_phone_1': '+639088835512',
            'mobile_phone_2': '+639088835513',
            'notes': 'Test note',
            'account': self.test_account.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contact.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'email', 'Enter a valid email address.')
        
    def test_form_invalid_mobile_phone_1(self):
        self.client.login(username='contact_create_user', password='password123')
        initial_count = Contact.objects.count()
        response = self.client.post(self.create_url, {
            'first_name': 'Test',
            'last_name': 'Invalid',
            'title': 'Manager',
            'department': 'Sales',
            'email': 'test@contact.com',
            'work_phone': '+639088835511',
            'mobile_phone_1': 'invalid_phone',
            'mobile_phone_2': '+639088835512',
            'notes': 'Test note',
            'account': self.test_account.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contact.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'mobile_phone_1', 'Enter a valid phone number (e.g., +639088835511).')

    def test_form_invalid_mobile_phone_2(self):
        self.client.login(username='contact_create_user', password='password123')
        initial_count = Contact.objects.count()
        response = self.client.post(self.create_url, {
            'first_name': 'Test',
            'last_name': 'Invalid',
            'title': 'Manager',
            'department': 'Sales',
            'email': 'test@contact.com',
            'work_phone': '+639088835511',
            'mobile_phone_1': '+639088835512',
            'mobile_phone_2': 'invalid_phone',
            'notes': 'Test note',
            'account': self.test_account.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contact.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'mobile_phone_2', 'Enter a valid phone number (e.g., +639088835511).')

    def test_form_invalid_email_format(self):
        self.client.login(username='contact_create_user', password='password123')
        initial_count = Contact.objects.count()
        response = self.client.post(self.create_url, {
            'first_name': 'Test',
            'last_name': 'Invalid',
            'title': 'Manager',
            'department': 'Sales',
            'email': 'invalid@.com',
            'work_phone': '+639088835511',
            'mobile_phone_1': '+639088835512',
            'mobile_phone_2': '+639088835513',
            'notes': 'Test note',
            'account': self.test_account.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contact.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'email', 'Enter a valid email address.')

class ContactDetailViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Users & Account needed for context
        cls.owner_user = create_user(username='cont_detail_owner', role=CustomUser.Roles.SALES)
        cls.other_user = create_user(username='cont_detail_other', role=CustomUser.Roles.SALES)
        cls.admin_user = create_user(username='cont_detail_admin', is_superuser=True)
        cls.account = Account.objects.create(name="Detail Contact Account", assigned_to=cls.owner_user)

        # Contact owned/assigned to owner_user
        cls.contact1 = Contact.objects.create(
            last_name="DetailContact",
            account=cls.account,
            created_by=cls.owner_user,
            assigned_to=cls.owner_user
        )
        cls.contact1_detail_url = reverse('crm_entities:contact-detail', kwargs={'pk': cls.contact1.pk})

    def test_detail_view_redirects_if_not_logged_in(self):
        response = self.client.get(self.contact1_detail_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.contact1_detail_url}')

    def test_detail_view_accessible_by_owner(self):
        self.client.login(username='cont_detail_owner', password='password123')
        response = self.client.get(self.contact1_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crm_entities/contact_detail.html')

    def test_detail_view_contains_contact_details(self):
        self.client.login(username='cont_detail_owner', password='password123')
        response = self.client.get(self.contact1_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.contact1.last_name)
        self.assertEqual(response.context['contact'], self.contact1)

    def test_detail_view_permission_denied_for_other_user(self):
        self.client.login(username='cont_detail_other', password='password123')
        response = self.client.get(self.contact1_detail_url)
        self.assertEqual(response.status_code, 404) # Expect 404 due to queryset filtering

    def test_detail_view_accessible_by_admin(self):
        self.client.login(username='cont_detail_admin', password='password123')
        response = self.client.get(self.contact1_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.contact1.last_name)


# --- Lead Detail View Tests ---
class LeadDetailViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
         # Users & Territory needed
        cls.owner_user = create_user(username='lead_detail_owner', role=CustomUser.Roles.SALES)
        cls.other_user = create_user(username='lead_detail_other', role=CustomUser.Roles.SALES)
        cls.admin_user = create_user(username='lead_detail_admin', is_superuser=True)

        # Lead owned/assigned to owner_user
        cls.lead1 = Lead.objects.create(
            last_name="DetailLead",
            company_name="Lead Detail Co",
            status=Lead.StatusChoices.QUALIFIED, # Use qualified for convert button check
            created_by=cls.owner_user,
            assigned_to=cls.owner_user
        )
        # Create a converted lead to test button visibility
        cls.lead_converted = Lead.objects.create(last_name="AlreadyConverted", status=Lead.StatusChoices.CONVERTED, assigned_to=cls.owner_user)

        cls.lead1_detail_url = reverse('crm_entities:lead-detail', kwargs={'pk': cls.lead1.pk})
        cls.lead_converted_detail_url = reverse('crm_entities:lead-detail', kwargs={'pk': cls.lead_converted.pk})


    def test_detail_view_redirects_if_not_logged_in(self):
        response = self.client.get(self.lead1_detail_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.lead1_detail_url}')

    def test_detail_view_accessible_by_owner(self):
        self.client.login(username='lead_detail_owner', password='password123')
        response = self.client.get(self.lead1_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crm_entities/lead_detail.html')

    def test_detail_view_contains_lead_details(self):
        self.client.login(username='lead_detail_owner', password='password123')
        response = self.client.get(self.lead1_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.lead1.last_name)
        self.assertContains(response, self.lead1.company_name)
        self.assertEqual(response.context['lead'], self.lead1)

    def test_detail_view_permission_denied_for_other_user(self):
        self.client.login(username='lead_detail_other', password='password123')
        response = self.client.get(self.lead1_detail_url)
        self.assertEqual(response.status_code, 404)

    def test_detail_view_accessible_by_admin(self):
        self.client.login(username='lead_detail_admin', password='password123')
        response = self.client.get(self.lead1_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.lead1.last_name)

    def test_convert_button_visibility_qualified(self):
        """ Test Convert button shows for QUALIFIED leads for authorized user """
        self.client.login(username='lead_detail_owner', password='password123')
        response = self.client.get(self.lead1_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Convert Lead') # Check button text/presence
        self.assertContains(response, reverse('crm_entities:lead-convert', kwargs={'pk': self.lead1.pk})) # Check form action URL

    def test_convert_button_visibility_converted(self):
        """ Test Convert button does NOT show for CONVERTED leads """
        self.client.login(username='lead_detail_owner', password='password123')
        response = self.client.get(self.lead_converted_detail_url)
        self.assertEqual(response.status_code, 200) # Should still be able to view
        self.assertNotContains(response, 'Convert Lead') # Button text should NOT be present

# Add more tests? e.g., for manager visibility based on territory


# Add these classes to the end of crm_entities/tests/test_views.py

# --- Lead Create View Tests ---
class LeadCreateViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.test_user = create_user(username='lead_create_user', role=CustomUser.Roles.SALES)
        # Territory might be needed if form field is required/used
        cls.territory = Territory.objects.create(name="Lead Create Territory")

    def setUp(self):
        self.client.login(username='lead_create_user', password='password123')
        self.create_url = reverse('crm_entities:lead-create')
        self.list_url = reverse('crm_entities:lead-list')

    def test_create_view_get_page_authenticated(self):
        """ Test GET request for create page loads for authenticated user """
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crm_entities/lead_form.html')
        self.assertContains(response, 'Create New Lead')

    def test_create_view_redirects_if_not_logged_in(self):
        self.client.logout()
        response = self.client.get(self.create_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.create_url}')

    def test_create_lead_success_post(self):
        """ Test successfully creating a lead via POST """
        initial_count = Lead.objects.count()
        lead_data = {
            'first_name': 'Test',
            'last_name': 'Lead', # Required
            'company_name': 'Test Lead Co',
            'status': Lead.StatusChoices.NEW, # Use a valid choice value
            'source': Lead.SourceChoices.WEBSITE, # Use a valid choice value
            'assigned_to': '', # Leave blank to test defaulting
            'territory': self.territory.pk,
            'email': 'test@lead.com'
            # Add other optional fields if needed
        }
        response = self.client.post(self.create_url, data=lead_data)

        self.assertRedirects(response, self.list_url)
        self.assertEqual(Lead.objects.count(), initial_count + 1)
        new_lead = Lead.objects.latest('created_at')
        self.assertEqual(new_lead.last_name, 'Lead')
        self.assertEqual(new_lead.created_by, self.test_user)
        self.assertEqual(new_lead.assigned_to, self.test_user) # Check default assigned_to
        self.assertEqual(new_lead.status, Lead.StatusChoices.NEW)

    def test_create_lead_missing_required_field(self):
        """ Test POST request fails if required field (last_name) is missing """
        initial_count = Lead.objects.count()
        lead_data = {
            'first_name': 'Test Missing',
            # 'last_name': 'Lead', # Missing required field
            'company_name': 'Test Lead Co',
            'status': Lead.StatusChoices.NEW,
            'territory': self.territory.pk,
        }
        response = self.client.post(self.create_url, data=lead_data)

        self.assertEqual(response.status_code, 200) # Should re-render form
        self.assertEqual(Lead.objects.count(), initial_count) # Count shouldn't change
        form_in_context = response.context.get('form')
        self.assertIsNotNone(form_in_context)
        self.assertFormError(form_in_context, 'last_name', 'This field is required.')
        self.assertTemplateUsed(response, 'crm_entities/lead_form.html')
        
    def test_form_invalid_email(self):
        self.client.login(username='lead_create_user', password='password123')
        initial_count = Lead.objects.count()
        response = self.client.post(self.create_url, {
            'first_name': 'Test',
            'last_name': 'Invalid',
            'company_name': 'Test Corp',
            'email': 'invalid_email',
            'status': Lead.StatusChoices.NEW,
            'source': 'Web',
            'territory': self.territory.pk,
            'assigned_to': self.test_user.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Lead.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'email', 'Enter a valid email address.')
        
    def test_form_invalid_work_phone(self):
        self.client.login(username='lead_create_user', password='password123')
        initial_count = Lead.objects.count()
        response = self.client.post(self.create_url, {
            'first_name': 'Test',
            'last_name': 'Invalid',
            'company_name': 'Test Corp',
            'email': 'test@lead.com',
            'work_phone': 'invalid_phone',
            'mobile_phone_1': '+6388019526',
            'mobile_phone_2': '+6388019527',
            'status': Lead.StatusChoices.NEW,
            'source': 'Web',
            'territory': self.territory.pk,
            'assigned_to': self.test_user.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Lead.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'work_phone', 'Enter a valid phone number (e.g., +6388019525).')

    def test_form_invalid_email_format(self):
        self.client.login(username='lead_create_user', password='password123')
        initial_count = Lead.objects.count()
        response = self.client.post(self.create_url, {
            'first_name': 'Test',
            'last_name': 'Invalid',
            'company_name': 'Test Corp',
            'email': 'invalid@.com',
            'work_phone': '+639088835511',
            'mobile_phone_1': '+639088835512',
            'mobile_phone_2': '+639088835513',
            'status': Lead.StatusChoices.NEW,
            'source': 'Web',
            'territory': self.territory.pk,
            'assigned_to': self.test_user.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Lead.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'email', 'Enter a valid email address.')
        
    def test_form_invalid_work_phone(self):
        self.client.login(username='lead_create_user', password='password123')
        initial_count = Lead.objects.count()
        response = self.client.post(self.create_url, {
            'first_name': 'Test',
            'last_name': 'Invalid',
            'company_name': 'Test Corp',
            'email': 'test@lead.com',
            'work_phone': 'invalid_phone',
            'status': Lead.StatusChoices.NEW,
            'source': 'Web',
            'territory': self.territory.pk,
            'assigned_to': self.test_user.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Lead.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'work_phone', 'Enter a valid phone number (e.g., +6388019525).')

    def test_form_invalid_email_format(self):
        self.client.login(username='lead_create_user', password='password123')
        initial_count = Lead.objects.count()
        response = self.client.post(self.create_url, {
            'first_name': 'Test',
            'last_name': 'Invalid',
            'company_name': 'Test Corp',
            'email': 'invalid@.com',
            'work_phone': '+639088835511',
            'mobile_phone_1': '+639088835512',
            'mobile_phone_2': '+639088835513',
            'status': Lead.StatusChoices.NEW,
            'source': 'Web',
            'territory': self.territory.pk,
            'assigned_to': self.test_user.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Lead.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'email', 'Enter a valid email address.')


# --- Contact Update View Tests ---
class ContactUpdateViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user(username='contact_update_owner', role=CustomUser.Roles.SALES)
        cls.other_user = create_user(username='contact_update_other', role=CustomUser.Roles.SALES)
        cls.admin_user = create_user(username='contact_update_admin', is_superuser=True)
        cls.account = Account.objects.create(name="Update Contact Account", assigned_to=cls.owner_user)
        cls.contact_to_update = Contact.objects.create(
            last_name="UpdateMe", account=cls.account, assigned_to=cls.owner_user
        )
        cls.update_url = reverse('crm_entities:contact-update', kwargs={'pk': cls.contact_to_update.pk})
        cls.list_url = reverse('crm_entities:contact-list')

    def test_update_view_get_page_as_owner(self):
        self.client.login(username='contact_update_owner', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crm_entities/contact_form.html')
        self.assertEqual(response.context['form'].initial['last_name'], self.contact_to_update.last_name)
        self.assertContains(response, 'Update Contact:')

    def test_update_view_get_permission_denied_for_other_user(self):
        self.client.login(username='contact_update_other', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 404)

    def test_update_contact_success_post_as_owner(self):
        self.client.login(username='contact_update_owner', password='password123')
        updated_last_name = "UpdatedLastName"
        updated_title = "Lead Tester"
        contact_data = {
            'first_name': self.contact_to_update.first_name or '',
            'last_name': updated_last_name,
            'title': updated_title,
            'account': self.contact_to_update.account.pk,
            'assigned_to': self.contact_to_update.assigned_to.pk,
            # Include other required fields from the form if any, or existing values
            'email': self.contact_to_update.email or '',
            'department': self.contact_to_update.department or '',
            'work_phone': self.contact_to_update.work_phone or '',
            'mobile_phone_1': self.contact_to_update.mobile_phone_1 or '',
            'mobile_phone_2': self.contact_to_update.mobile_phone_2 or '',
            'notes': self.contact_to_update.notes or '',
        }
        response = self.client.post(self.update_url, data=contact_data)
        self.assertRedirects(response, self.list_url)
        self.contact_to_update.refresh_from_db()
        self.assertEqual(self.contact_to_update.last_name, updated_last_name)
        self.assertEqual(self.contact_to_update.title, updated_title)


# --- Lead Update View Tests ---
class LeadUpdateViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user(username='lead_update_owner', role=CustomUser.Roles.SALES)
        cls.other_user = create_user(username='lead_update_other', role=CustomUser.Roles.SALES)
        cls.territory = Territory.objects.create(name="Lead Update Territory")
        cls.lead_to_update = Lead.objects.create(
            last_name="LeadToUpdate", company_name="Update Co", status=Lead.StatusChoices.NEW,
            assigned_to=cls.owner_user, territory=cls.territory
        )
        cls.update_url = reverse('crm_entities:lead-update', kwargs={'pk': cls.lead_to_update.pk})
        cls.list_url = reverse('crm_entities:lead-list')

    def test_update_view_get_page_as_owner(self):
        self.client.login(username='lead_update_owner', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crm_entities/lead_form.html')
        self.assertEqual(response.context['form'].initial['last_name'], self.lead_to_update.last_name)
        self.assertContains(response, 'Update Lead:')

    def test_update_view_get_permission_denied_for_other_user(self):
        self.client.login(username='lead_update_other', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 404)

    def test_update_lead_success_post_as_owner(self):
        self.client.login(username='lead_update_owner', password='password123')
        updated_last_name = "UpdatedLeadName"
        updated_status = Lead.StatusChoices.QUALIFIED
        lead_data = {
            'first_name': self.lead_to_update.first_name or '',
            'last_name': updated_last_name,
            'company_name': self.lead_to_update.company_name,
            'status': updated_status,
            'source': self.lead_to_update.source or '',
            'territory': self.lead_to_update.territory.pk,
            'assigned_to': self.lead_to_update.assigned_to.pk,
            'email': self.lead_to_update.email or ''
        }
        response = self.client.post(self.update_url, data=lead_data)
        self.assertRedirects(response, self.list_url)
        self.lead_to_update.refresh_from_db()
        self.assertEqual(self.lead_to_update.last_name, updated_last_name)
        self.assertEqual(self.lead_to_update.status, updated_status)
        
        
# Add these classes to the end of crm_entities/tests/test_views.py

# --- Account Delete View Tests ---
class AccountDeleteViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user(username='acc_delete_owner', role=CustomUser.Roles.SALES)
        cls.other_user = create_user(username='acc_delete_other', role=CustomUser.Roles.SALES)
        cls.admin_user = create_user(username='acc_delete_admin', is_superuser=True)

        cls.account_to_delete = Account.objects.create(name="Delete Me Account", assigned_to=cls.owner_user)
        cls.delete_url = reverse('crm_entities:account-delete', kwargs={'pk': cls.account_to_delete.pk})
        cls.list_url = reverse('crm_entities:account-list')

    def test_delete_view_get_page_as_owner(self):
        """ Test GET request loads confirmation page for owner """
        self.client.login(username='acc_delete_owner', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crm_entities/account_confirm_delete.html')
        self.assertContains(response, 'Are you sure you want to delete')
        self.assertContains(response, self.account_to_delete.name)

    def test_delete_view_get_permission_denied_for_other_user(self):
        """ Test other user gets 404 trying to access delete confirmation page """
        self.client.login(username='acc_delete_other', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 404)

    def test_delete_account_success_post_as_owner(self):
        """ Test successfully deleting an account via POST as owner """
        self.client.login(username='acc_delete_owner', password='password123')
        initial_count = Account.objects.count()
        response = self.client.post(self.delete_url) # POST to confirm deletion

        # Check for successful redirect to the list page
        self.assertRedirects(response, self.list_url)
        # Check that one account was deleted
        self.assertEqual(Account.objects.count(), initial_count - 1)
        # Check that the specific account no longer exists
        self.assertFalse(Account.objects.filter(pk=self.account_to_delete.pk).exists())

    def test_delete_account_permission_denied_post_other_user(self):
        """ Test POST delete fails for user without permission """
        self.client.login(username='acc_delete_other', password='password123')
        initial_count = Account.objects.count()
        response = self.client.post(self.delete_url)
        # Should get 404 because get_queryset prevents access before deletion happens
        self.assertEqual(response.status_code, 404)
        # Verify object was NOT deleted
        self.assertEqual(Account.objects.count(), initial_count)
        self.assertTrue(Account.objects.filter(pk=self.account_to_delete.pk).exists())


# --- Contact Delete View Tests ---
class ContactDeleteViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user(username='cont_delete_owner', role=CustomUser.Roles.SALES)
        cls.other_user = create_user(username='cont_delete_other', role=CustomUser.Roles.SALES)
        cls.test_account = Account.objects.create(name="Delete Contact Account", assigned_to=cls.owner_user)
        cls.contact_to_delete = Contact.objects.create(last_name="DeleteMeContact", account=cls.test_account, assigned_to=cls.owner_user)
        cls.delete_url = reverse('crm_entities:contact-delete', kwargs={'pk': cls.contact_to_delete.pk})
        cls.list_url = reverse('crm_entities:contact-list')

    def test_delete_view_get_page_as_owner(self):
        self.client.login(username='cont_delete_owner', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crm_entities/contact_confirm_delete.html')
        self.assertContains(response, self.contact_to_delete.last_name)

    def test_delete_view_get_permission_denied_for_other_user(self):
        self.client.login(username='cont_delete_other', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 404)

    def test_delete_contact_success_post_as_owner(self):
        self.client.login(username='cont_delete_owner', password='password123')
        initial_count = Contact.objects.count()
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(Contact.objects.count(), initial_count - 1)
        self.assertFalse(Contact.objects.filter(pk=self.contact_to_delete.pk).exists())


# --- Lead Delete View Tests ---
class LeadDeleteViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user(username='lead_delete_owner', role=CustomUser.Roles.SALES)
        cls.other_user = create_user(username='lead_delete_other', role=CustomUser.Roles.SALES)
        cls.lead_to_delete = Lead.objects.create(last_name="DeleteMeLead", company_name="Delete Co", assigned_to=cls.owner_user)
        cls.delete_url = reverse('crm_entities:lead-delete', kwargs={'pk': cls.lead_to_delete.pk})
        cls.list_url = reverse('crm_entities:lead-list')

    def test_delete_view_get_page_as_owner(self):
        self.client.login(username='lead_delete_owner', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crm_entities/lead_confirm_delete.html')
        self.assertContains(response, self.lead_to_delete.last_name)

    def test_delete_view_get_permission_denied_for_other_user(self):
        self.client.login(username='lead_delete_other', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 404)

    def test_delete_lead_success_post_as_owner(self):
        self.client.login(username='lead_delete_owner', password='password123')
        initial_count = Lead.objects.count()
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(Lead.objects.count(), initial_count - 1)
        self.assertFalse(Lead.objects.filter(pk=self.lead_to_delete.pk).exists())
        


class LeadConvertViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create users first
        cls.test_user = create_user(username='lead_convert_user_v3', role=CustomUser.Roles.SALES)
        cls.other_user = create_user('convert_other_user_v3', role=CustomUser.Roles.SALES)

        # Create leads AFTER users, ensuring assignment is clear
        # Use very distinct names to help database query later if needed
        cls.lead_to_convert = Lead.objects.create(
            first_name="Ready_v3", last_name="ToConvert", company_name="ConvertCorp Success Test v3",
            email="convert_v3@example.com", status=Lead.StatusChoices.QUALIFIED,
            assigned_to=cls.test_user, created_by=cls.test_user
        )
        cls.lead_already_converted = Lead.objects.create(
            first_name="Already_v3", last_name="Done", company_name="Converted Inc Test v3",
            email="done_v3@example.com", status=Lead.StatusChoices.CONVERTED,
            assigned_to=cls.test_user, created_by=cls.test_user
        )
        cls.other_lead = Lead.objects.create(
            last_name="OtherLeadToConvert_v3", status=Lead.StatusChoices.QUALIFIED, assigned_to=cls.other_user
        )

    def setUp(self):
        # Login the primary test user for most tests
        self.client.login(username='lead_convert_user_v3', password='password123')
        # Define URLs within setUp or test methods using correct PKs directly
        self.convert_url = reverse('crm_entities:lead-convert', kwargs={'pk': self.lead_to_convert.pk})
        self.already_converted_url = reverse('crm_entities:lead-convert', kwargs={'pk': self.lead_already_converted.pk})
        self.other_convert_url = reverse('crm_entities:lead-convert', kwargs={'pk': self.other_lead.pk})
        self.other_lead_detail_url = reverse('crm_entities:lead-detail', kwargs={'pk': self.other_lead.pk})

    def test_convert_lead_success(self):
        """ Test successful lead conversion via POST request """
        initial_account_count = Account.objects.count()
        initial_contact_count = Contact.objects.count()
        initial_deal_count = Deal.objects.count()

        # Use the specific URL for the lead we want to convert
        response = self.client.post(self.convert_url)

        # 1. Check Redirect Status and Target URL FIRST
        self.assertEqual(response.status_code, 302, f"POST request failed, status code {response.status_code} != 302. Check terminal for errors.")

        # Find the expected account *after* confirming redirect happened
        # Use a more specific filter now we have unique name
        new_account = Account.objects.filter(name="ConvertCorp Success Test v3").first()
        self.assertIsNotNone(new_account, "New account 'ConvertCorp Success Test v3' should have been created")

        expected_redirect_url = reverse('crm_entities:account-detail', kwargs={'pk': new_account.pk})
        self.assertEqual(response.url, expected_redirect_url, "Should redirect to the new account's detail page.")

        # 2. Check Object Creation
        self.assertEqual(Account.objects.count(), initial_account_count + 1, "Account count should increment")
        self.assertEqual(Contact.objects.count(), initial_contact_count + 1, "Contact count should increment")
        self.assertEqual(Deal.objects.count(), initial_deal_count + 1, "Deal count should increment")

        # 3. Check Lead Status Update
        self.lead_to_convert.refresh_from_db()
        self.assertEqual(self.lead_to_convert.status, Lead.StatusChoices.CONVERTED, "Lead status should be CONVERTED")

        # 4. Check Links (Optional but good)
        new_contact = Contact.objects.get(email="convert_v3@example.com")
        new_deal = Deal.objects.get(account=new_account) # Find deal linked to account
        self.assertEqual(new_contact.account, new_account)
        self.assertEqual(new_deal.primary_contact, new_contact)

    def test_convert_already_converted_lead(self):
        """ Test attempting to convert an already converted lead """
        initial_account_count = Account.objects.count()
        response = self.client.post(self.already_converted_url)
        # Check it redirects back to the lead detail page
        expected_redirect_url = reverse('crm_entities:lead-detail', kwargs={'pk': self.lead_already_converted.pk})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected_redirect_url)
        # Check no new objects were created
        self.assertEqual(Account.objects.count(), initial_account_count)

    def test_convert_permission_denied(self):
        """ Test converting a lead not assigned to user fails and redirects correctly """
        initial_account_count = Account.objects.count()
        response = self.client.post(self.other_convert_url) # User 'lead_convert_user_v3' tries to convert 'other_lead'

        # Check it redirects (302) back to the detail page of the lead they TRIED to convert
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.other_lead_detail_url)

        # Verify no conversion actually happened
        self.assertEqual(Account.objects.count(), initial_account_count)
        self.other_lead.refresh_from_db()
        self.assertEqual(self.other_lead.status, Lead.StatusChoices.QUALIFIED) # Status should not change
        
    def test_convert_invalid_lead(self):
        self.client.login(username='lead_convert_user_v3', password='password123')
        invalid_url = reverse('crm_entities:lead-convert', kwargs={'pk': 999})
        response = self.client.post(invalid_url)
        self.assertEqual(response.status_code, 302)  # Redirects to list page
        self.assertRedirects(response, reverse('crm_entities:lead-list'))
        
    def test_convert_with_empty_data(self):
        self.client.login(username='lead_convert_user_v3', password='password123')
        initial_account_count = Account.objects.count()
        response = self.client.post(self.convert_url, {})
        self.assertEqual(response.status_code, 302)  # Redirects to new account
        self.assertEqual(Account.objects.count(), initial_account_count + 1)  # New account created
        self.lead_to_convert.refresh_from_db()
        self.assertEqual(self.lead_to_convert.status, Lead.StatusChoices.CONVERTED)  # Lead converted
        new_account = Account.objects.latest('created_at')
        self.assertRedirects(response, reverse('crm_entities:account-detail', kwargs={'pk': new_account.pk}))

# --- Export View Tests ---
class CrmEntitiesExportViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create users with different roles
        cls.sales_user = create_user(username='export_test_sales', role=CustomUser.Roles.SALES)
        cls.manager_user = create_user(username='export_test_manager', role=CustomUser.Roles.MANAGER)
        cls.admin_user = create_user(username='export_test_admin', is_superuser=True)

        # URLs for export views
        cls.account_export_url = reverse('crm_entities:account-export')
        cls.contact_export_url = reverse('crm_entities:contact-export')
        cls.lead_export_url = reverse('crm_entities:lead-export')

    # Test Permissions (Non-Admins should be Forbidden)
    def test_export_permission_denied_for_sales(self):
        self.client.login(username='export_test_sales', password='password123')
        response_acc = self.client.get(self.account_export_url)
        response_con = self.client.get(self.contact_export_url)
        response_lead = self.client.get(self.lead_export_url)
        self.assertEqual(response_acc.status_code, 403, "Sales user should get 403 Forbidden for account export")
        self.assertEqual(response_con.status_code, 403, "Sales user should get 403 Forbidden for contact export")
        self.assertEqual(response_lead.status_code, 403, "Sales user should get 403 Forbidden for lead export")

    def test_export_permission_denied_for_manager(self):
        self.client.login(username='export_test_manager', password='password123')
        response_acc = self.client.get(self.account_export_url)
        response_con = self.client.get(self.contact_export_url)
        response_lead = self.client.get(self.lead_export_url)
        self.assertEqual(response_acc.status_code, 403, "Manager should get 403 Forbidden for account export")
        self.assertEqual(response_con.status_code, 403, "Manager should get 403 Forbidden for contact export")
        self.assertEqual(response_lead.status_code, 403, "Manager should get 403 Forbidden for lead export")

    # Test Success for Admin
    def test_account_export_success_for_admin(self):
        self.client.login(username='export_test_admin', password='password123')
        response = self.client.get(self.account_export_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertTrue(response['content-disposition'].startswith('attachment; filename="accounts_export.xlsx"'))

    def test_contact_export_success_for_admin(self):
        self.client.login(username='export_test_admin', password='password123')
        response = self.client.get(self.contact_export_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertTrue(response['content-disposition'].startswith('attachment; filename="contacts_export.xlsx"'))

    def test_lead_export_success_for_admin(self):
        self.client.login(username='export_test_admin', password='password123')
        response = self.client.get(self.lead_export_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertTrue(response['content-disposition'].startswith('attachment; filename="leads_export.xlsx"'))

    # Test redirect if not logged in
    def test_export_redirects_if_not_logged_in(self):
        self.client.logout()
        response = self.client.get(self.account_export_url) # Test one is enough
        login_url = reverse('login')
        # Note: @login_required redirects differently than LoginRequiredMixin
        # It might redirect directly to login without the ?next= part for simple GET
        # Let's check for redirect status first, then target URL if needed
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(login_url))

# --- End Export View Tests ---

# Add this class to the end of crm_entities/tests/test_views.py


# --- Autocomplete View Tests ---
class CrmEntitiesAutocompleteViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Users
        cls.admin_user = create_user(username='auto_admin', is_superuser=True)
        cls.manager_user = create_user(username='auto_manager', role=CustomUser.Roles.MANAGER)
        cls.sales_user1 = create_user(username='auto_sales1', role=CustomUser.Roles.SALES)
        cls.sales_user2 = create_user(username='auto_sales2', role=CustomUser.Roles.SALES)

        # Territories & Manager Assignment
        cls.t1 = Territory.objects.create(name="Autocomplete Territory 1")
        cls.manager_user.managed_territories.add(cls.t1)
        cls.sales_user1.territory = cls.t1
        cls.sales_user1.save()

        # Accounts
        cls.acc1 = Account.objects.create(name="Alpha Test Account", assigned_to=cls.sales_user1, territory=cls.t1)
        cls.acc2 = Account.objects.create(name="Beta Test Account", assigned_to=cls.sales_user2)
        cls.acc3 = Account.objects.create(name="Gamma Admin Account", assigned_to=cls.admin_user)

        # Contacts (Link some to acc1 for forwarding test)
        cls.cont1 = Contact.objects.create(last_name="ContactAlpha", account=cls.acc1, assigned_to=cls.sales_user1)
        cls.cont2 = Contact.objects.create(last_name="ContactBeta", account=cls.acc2, assigned_to=cls.sales_user2)
        cls.cont3 = Contact.objects.create(last_name="ContactAlpha2", account=cls.acc1, assigned_to=cls.sales_user1) # Another for acc1

        # Leads
        cls.lead1 = Lead.objects.create(last_name="LeadAlpha", status=Lead.StatusChoices.QUALIFIED, assigned_to=cls.sales_user1)
        cls.lead2 = Lead.objects.create(last_name="LeadBeta", status=Lead.StatusChoices.NEW, assigned_to=cls.sales_user2)

        # Deal (Needed for contact forwarding test)
        # Ensure Deal model import is available if not already global
        from sales_pipeline.models import Deal
        cls.deal_for_acc1 = Deal.objects.create(name="Deal for Acc1", account=cls.acc1, stage=Deal.StageChoices.PROSPECTING, amount=100, close_date=date.today())


        # URLs
        cls.acc_auto_url = reverse('crm_entities:account-autocomplete')
        cls.cont_auto_url = reverse('crm_entities:contact-autocomplete')
        cls.lead_auto_url = reverse('crm_entities:lead-autocomplete')

    # --- Account Autocomplete Tests ---

    def test_account_autocomplete_login_required(self):
        """ Test autocomplete view redirects if not logged in """
        response = self.client.get(self.acc_auto_url) # Make request without login
        login_url = reverse('login')
        # Check it redirects to login page, appending the original URL as 'next'
        self.assertRedirects(response, f'{login_url}?next={self.acc_auto_url}')

    def test_account_autocomplete_admin_search(self):
        self.client.login(username='auto_admin', password='password123')
        response = self.client.get(self.acc_auto_url, data={'q': 'Test Account'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        content = json.loads(response.content)
        self.assertIn('results', content)
        # Admin sees all accounts matching
        self.assertEqual(len(content['results']), 2) # Alpha Test Account, Beta Test Account
        result_names = {r['text'] for r in content['results']}
        self.assertIn("Alpha Test Account", result_names)
        self.assertIn("Beta Test Account", result_names)
        self.assertNotIn("Gamma Admin Account", result_names) # Doesn't contain 'Test Account'

    def test_account_autocomplete_sales_permissions(self):
        self.client.login(username='auto_sales2', password='password123') # Sales user 2
        response = self.client.get(self.acc_auto_url, data={'q': 'Account'}) # Search broadly
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        # Sales user 2 should only see acc2 (Beta Test Account) based on simple assign/create logic
        self.assertEqual(len(content['results']), 1)
        self.assertEqual(content['results'][0]['text'], "Beta Test Account")

    # --- Contact Autocomplete Tests ---

    def test_contact_autocomplete_basic_search(self):
        self.client.login(username='auto_admin', password='password123')
        response = self.client.get(self.cont_auto_url, data={'q': 'Alpha'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        content = json.loads(response.content)
        self.assertIn('results', content)
        # Should find ContactAlpha and ContactAlpha2
        self.assertEqual(len(content['results']), 2)

    def test_contact_autocomplete_forwarding(self):
        """ Test that contact results are filtered by deal's account when deal is forwarded """
        self.client.login(username='auto_admin', password='password123')
        # Request contacts related to the deal linked to acc1
        response = self.client.get(self.cont_auto_url, data={'forward': json.dumps({'deal': self.deal_for_acc1.pk})})
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertIn('results', content)
        # Should only see contacts linked to acc1 (cont1, cont3)
        self.assertEqual(len(content['results']), 2)
        result_names = {r['text'] for r in content['results']}
        self.assertIn("ContactAlpha", result_names)
        self.assertIn("ContactAlpha2", result_names)

        # Request contacts related to a non-existent deal pk (should return none)
        response_bad_deal = self.client.get(self.cont_auto_url, data={'forward': json.dumps({'deal': 9999})})
        self.assertEqual(response_bad_deal.status_code, 200)
        content_bad_deal = json.loads(response_bad_deal.content)
        self.assertEqual(len(content_bad_deal['results']), 0)

    # --- Lead Autocomplete Tests ---

    def test_lead_autocomplete_excludes_converted(self):
        self.client.login(username='auto_admin', password='password123')
        # Create a converted lead for this test that shouldn't appear
        Lead.objects.create(last_name="ShouldNotAppear", status=Lead.StatusChoices.CONVERTED, assigned_to=self.admin_user)
        response = self.client.get(self.lead_auto_url, data={'q': 'Lead'}) # Search broadly
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        result_names = {r['text'] for r in content['results']}
        # Should find LeadAlpha and LeadBeta, but not ShouldNotAppear or ConvertedLeadTest from other class
        self.assertIn("LeadAlpha", result_names)
        self.assertIn("LeadBeta", result_names)
        self.assertNotIn("ShouldNotAppear", result_names)
        self.assertNotIn("ConvertedLeadTest", result_names) # Check from other test class isn't leaking if run together

# --- End Autocomplete View Tests ---