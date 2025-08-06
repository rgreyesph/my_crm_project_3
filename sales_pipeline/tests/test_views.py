from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
import re
from decimal import Decimal
import openpyxl
import io
from unittest.mock import patch
from django.db.models import Q

# Import models needed for setup and testing
from users.models import CustomUser
from sales_territories.models import Territory
from crm_entities.models import Account, Contact
from ..models import Deal, Quote


# Helper function
def create_user(
    username,
    password="password123",
    role=CustomUser.Roles.SALES,
    territory=None,
    is_superuser=False
):
    """ Creates a user with specified role/territory """
    if is_superuser:
        return CustomUser.objects.create_superuser(
            username=username,
            password=password,
            email=f"{username}@example.com",
            role=CustomUser.Roles.ADMIN
        )
    else:
        return CustomUser.objects.create_user(
            username=username,
            password=password,
            role=role,
            territory=territory,
            email=f"{username}@example.com"
        )


# BaseSalesPipelineView Tests
class BaseSalesPipelineViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.manager_user = create_user(
            'base_manager',
            role=CustomUser.Roles.MANAGER
        )
        cls.t1 = Territory.objects.create(name="Base Test Territory")
        cls.manager_user.managed_territories.add(cls.t1)

    def test_filter_queryset_by_role_exception(self):
        from sales_pipeline.views import BaseSalesPipelineView
        view = BaseSalesPipelineView()
        view.model = Deal
        with patch(
            'django.db.models.fields.related_descriptors.create_reverse_many_to_one_manager',
            side_effect=Exception("Database error")
        ):
            queryset = Deal.objects.all()
            filtered = view._filter_queryset_by_role(self.manager_user, queryset)
            self.assertEqual(
                filtered.count(),
                queryset.filter(
                    Q(assigned_to=self.manager_user) |
                    Q(created_by=self.manager_user)
                ).count()
            )


# Deal List View Tests
class DealListViewPermissionTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = create_user('deal_list_admin_v2', is_superuser=True)
        cls.manager_user = create_user(
            'deal_list_manager_v2',
            role=CustomUser.Roles.MANAGER
        )
        cls.t1 = Territory.objects.create(name="Deal Test Territory 1 v2")
        cls.t2 = Territory.objects.create(name="Deal Test Territory 2 v2")
        cls.sales_user1 = create_user(
            'deal_list_sales1_v2',
            role=CustomUser.Roles.SALES,
            territory=cls.t1
        )
        cls.sales_user2 = create_user(
            'deal_list_sales2_v2',
            role=CustomUser.Roles.SALES,
            territory=cls.t2
        )
        cls.empty_sales_user = create_user(
            'deal_list_empty_sales',
            role=CustomUser.Roles.SALES,
            territory=cls.t2
        )
        cls.manager_user.managed_territories.add(cls.t1)

        cls.acc_t1_s1 = Account.objects.create(
            name="Deal Acc 1 (T1/S1)",
            territory=cls.t1,
            assigned_to=cls.sales_user1
        )
        cls.acc_t2_s2 = Account.objects.create(
            name="Deal Acc 2 (T2/S2)",
            territory=cls.t2,
            assigned_to=cls.sales_user2
        )
        cls.acc_t1_mgr = Account.objects.create(
            name="Deal Acc Mgr (T1/Mgr)",
            territory=cls.t1,
            assigned_to=cls.manager_user
        )
        cls.acc_admin = Account.objects.create(
            name="Deal Acc Admin (No T)",
            assigned_to=cls.admin_user
        )

        cls.deal1 = Deal.objects.create(
            name="Admin Deal",
            account=cls.acc_admin,
            stage=Deal.StageChoices.PROSPECTING,
            amount=1000,
            close_date=date.today(),
            assigned_to=cls.admin_user
        )
        cls.deal2 = Deal.objects.create(
            name="Manager Deal",
            account=cls.acc_t1_mgr,
            stage=Deal.StageChoices.QUALIFICATION,
            amount=2000,
            close_date=date.today(),
            assigned_to=cls.manager_user
        )
        cls.deal3 = Deal.objects.create(
            name="Sales1 Deal 1",
            account=cls.acc_t1_s1,
            stage=Deal.StageChoices.PROPOSAL,
            amount=3000,
            close_date=date.today(),
            assigned_to=cls.sales_user1
        )
        cls.deal4 = Deal.objects.create(
            name="Sales1 Deal 2",
            account=cls.acc_t1_mgr,
            stage=Deal.StageChoices.NEGOTIATION,
            amount=4000,
            close_date=date.today(),
            assigned_to=cls.sales_user1
        )
        cls.deal5 = Deal.objects.create(
            name="Sales2 Deal",
            account=cls.acc_t2_s2,
            stage=Deal.StageChoices.PROSPECTING,
            amount=5000,
            close_date=date.today(),
            assigned_to=cls.sales_user2
        )

        cls.deal_list_url = reverse('sales_pipeline:deal-list')

    def test_url_and_template(self):
        self.client.login(username='deal_list_admin_v2', password='password123')
        response = self.client.get(self.deal_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sales_pipeline/deal_list.html')

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.deal_list_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.deal_list_url}')

    def test_admin_sees_all_deals(self):
        self.client.login(username='deal_list_admin_v2', password='password123')
        response = self.client.get(self.deal_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['deals']), 5)

    def test_sales_user_sees_only_own_deals(self):
        self.client.login(username='deal_list_sales1_v2', password='password123')
        response = self.client.get(self.deal_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['deals']), 2)
        deal_names = {d.name for d in response.context['deals']}
        self.assertIn(self.deal3.name, deal_names)
        self.assertIn(self.deal4.name, deal_names)

    def test_manager_sees_own_team_and_territory_deals(self):
        self.client.login(username='deal_list_manager_v2', password='password123')
        response = self.client.get(self.deal_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['deals']), 3)
        deal_names = {d.name for d in response.context['deals']}
        self.assertIn(self.deal2.name, deal_names)
        self.assertIn(self.deal3.name, deal_names)
        self.assertIn(self.deal4.name, deal_names)
        self.assertNotIn(self.deal1.name, deal_names)
        self.assertNotIn(self.deal5.name, deal_names)

    def test_invalid_sort_param(self):
        self.client.login(username='deal_list_admin_v2', password='password123')
        response = self.client.get(self.deal_list_url, {'sort': 'invalid_field'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sort_by'], 'deal_id')
        self.assertEqual(response.context['direction'], 'desc')

    def test_empty_queryset(self):
        self.client.login(username='deal_list_empty_sales', password='password123')
        response = self.client.get(self.deal_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['deals']), 0)


# Quote List View Tests
class QuoteListViewPermissionTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = create_user('quote_list_admin', is_superuser=True)
        cls.manager_user = create_user('quote_list_manager', role=CustomUser.Roles.MANAGER)
        cls.t1 = Territory.objects.create(name="Quote Test Territory 1")
        cls.sales_user1 = create_user(
            'quote_list_sales1',
            role=CustomUser.Roles.SALES,
            territory=cls.t1
        )
        cls.sales_user2 = create_user(
            'quote_list_sales2',
            role=CustomUser.Roles.SALES
        )
        cls.empty_sales_user = create_user(
            'quote_list_empty_sales',
            role=CustomUser.Roles.SALES,
            territory=cls.t1
        )
        cls.manager_user.managed_territories.add(cls.t1)

        cls.acc1 = Account.objects.create(
            name="Quote Acc 1 (T1)",
            territory=cls.t1,
            assigned_to=cls.sales_user1
        )
        cls.acc2 = Account.objects.create(
            name="Quote Acc 2 (Other)",
            assigned_to=cls.sales_user2
        )
        cls.acc_mgr = Account.objects.create(
            name="Quote Acc Mgr",
            territory=cls.t1,
            assigned_to=cls.manager_user
        )

        cls.deal1 = Deal.objects.create(
            name="Deal for Quote 1",
            account=cls.acc1,
            assigned_to=cls.sales_user1,
            stage=Deal.StageChoices.PROPOSAL,
            amount=100,
            close_date=date.today()
        )
        cls.deal2 = Deal.objects.create(
            name="Deal for Quote 2",
            account=cls.acc2,
            assigned_to=cls.sales_user2,
            stage=Deal.StageChoices.PROPOSAL,
            amount=100,
            close_date=date.today()
        )
        cls.deal_mgr = Deal.objects.create(
            name="Deal for Quote Mgr",
            account=cls.acc_mgr,
            assigned_to=cls.manager_user,
            stage=Deal.StageChoices.PROPOSAL,
            amount=100,
            close_date=date.today()
        )

        cls.quote1 = Quote.objects.create(
            deal=cls.deal1,
            status=Quote.StatusChoices.DRAFT,
            assigned_to=cls.sales_user1
        )
        cls.quote2 = Quote.objects.create(
            deal=cls.deal2,
            status=Quote.StatusChoices.PRESENTED,
            assigned_to=cls.sales_user2
        )
        cls.quote_mgr = Quote.objects.create(
            deal=cls.deal_mgr,
            status=Quote.StatusChoices.DRAFT,
            assigned_to=cls.manager_user
        )

        cls.quote_list_url = reverse('sales_pipeline:quote-list')

    def test_url_and_template(self):
        self.client.login(username='quote_list_admin', password='password123')
        response = self.client.get(self.quote_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sales_pipeline/quote_list.html')

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.quote_list_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.quote_list_url}')

    def test_admin_sees_all_quotes(self):
        self.client.login(username='quote_list_admin', password='password123')
        response = self.client.get(self.quote_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['quotes']), 3)

    def test_sales_user_sees_only_own_quotes(self):
        self.client.login(username='quote_list_sales1', password='password123')
        response = self.client.get(self.quote_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['quotes']), 1)
        self.assertEqual(response.context['quotes'][0], self.quote1)

    def test_manager_sees_own_team_and_territory_quotes(self):
        self.client.login(username='quote_list_manager', password='password123')
        response = self.client.get(self.quote_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['quotes']), 2)
        quote_ids = {q.pk for q in response.context['quotes']}
        self.assertIn(self.quote_mgr.pk, quote_ids)
        self.assertIn(self.quote1.pk, quote_ids)

    def test_invalid_sort_param(self):
        self.client.login(username='quote_list_admin', password='password123')
        response = self.client.get(self.quote_list_url, {'sort': 'invalid_field'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sort_by'], 'quote_id')
        self.assertEqual(response.context['direction'], 'desc')

    def test_empty_queryset(self):
        self.client.login(username='quote_list_empty_sales', password='password123')
        response = self.client.get(self.quote_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['quotes']), 0)


# Deal Detail View Tests
class DealDetailViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user(
            username='deal_detail_owner',
            role=CustomUser.Roles.SALES
        )
        cls.other_user = create_user(
            username='deal_detail_other',
            role=CustomUser.Roles.SALES
        )
        cls.admin_user = create_user(
            username='deal_detail_admin',
            is_superuser=True
        )
        cls.account = Account.objects.create(
            name="Detail Deal Account",
            assigned_to=cls.owner_user
        )

        cls.deal1 = Deal.objects.create(
            name="Detail Test Deal Alpha",
            account=cls.account,
            stage=Deal.StageChoices.QUALIFICATION,
            amount=5000,
            close_date=date.today() + timedelta(days=60),
            created_by=cls.owner_user,
            assigned_to=cls.owner_user
        )
        cls.deal1_detail_url = reverse(
            'sales_pipeline:deal-detail',
            kwargs={'pk': cls.deal1.pk}
        )

    def test_detail_view_redirects_if_not_logged_in(self):
        response = self.client.get(self.deal1_detail_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.deal1_detail_url}')

    def test_detail_view_accessible_by_owner(self):
        self.client.login(username='deal_detail_owner', password='password123')
        response = self.client.get(self.deal1_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sales_pipeline/deal_detail.html')

    def test_detail_view_contains_deal_details(self):
        self.client.login(username='deal_detail_owner', password='password123')
        response = self.client.get(self.deal1_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.deal1.name)
        self.assertContains(response, self.deal1.account.name)
        self.assertEqual(response.context['deal'], self.deal1)

    def test_detail_view_permission_denied_for_other_user(self):
        self.client.login(username='deal_detail_other', password='password123')
        response = self.client.get(self.deal1_detail_url)
        self.assertEqual(response.status_code, 404)

    def test_detail_view_accessible_by_admin(self):
        self.client.login(username='deal_detail_admin', password='password123')
        response = self.client.get(self.deal1_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.deal1.name)


# Quote Detail View Tests
class QuoteDetailViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = create_user(username='quote_detail_admin', is_superuser=True)
        cls.manager_user = create_user(
            'quote_detail_manager',
            role=CustomUser.Roles.MANAGER
        )
        cls.t1 = Territory.objects.create(name="Quote Detail Territory")
        cls.sales_user1 = create_user(
            'quote_detail_sales1',
            role=CustomUser.Roles.SALES,
            territory=cls.t1
        )
        cls.sales_user2 = create_user(
            'quote_detail_other',
            role=CustomUser.Roles.SALES
        )
        cls.manager_user.managed_territories.add(cls.t1)

        cls.acc1 = Account.objects.create(
            name="Quote Detail Account",
            territory=cls.t1,
            assigned_to=cls.sales_user1
        )
        cls.deal1 = Deal.objects.create(
            name="Deal for Quote Detail",
            account=cls.acc1,
            stage=Deal.StageChoices.PROPOSAL,
            amount=100,
            close_date=date.today(),
            assigned_to=cls.sales_user1
        )

        cls.quote1 = Quote.objects.create(
            deal=cls.deal1,
            status=Quote.StatusChoices.PRESENTED,
            total_amount=100,
            created_by=cls.sales_user1,
            assigned_to=cls.sales_user1,
            presented_date=date.today()
        )
        cls.quote1.refresh_from_db()
        cls.quote1_detail_url = reverse(
            'sales_pipeline:quote-detail',
            kwargs={'pk': cls.quote1.pk}
        )

    def test_detail_view_redirects_if_not_logged_in(self):
        response = self.client.get(self.quote1_detail_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.quote1_detail_url}')

    def test_detail_view_accessible_by_owner(self):
        self.client.login(username='quote_detail_sales1', password='password123')
        response = self.client.get(self.quote1_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sales_pipeline/quote_detail.html')

    def test_detail_view_contains_quote_details(self):
        self.client.login(username='quote_detail_sales1', password='password123')
        response = self.client.get(self.quote1_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(self.quote1.quote_id)
        self.assertContains(response, self.quote1.quote_id)
        self.assertContains(response, self.quote1.deal.name)
        self.assertEqual(response.context['quote'], self.quote1)

    def test_detail_view_permission_denied_for_other_user(self):
        self.client.login(username='quote_detail_other', password='password123')
        response = self.client.get(self.quote1_detail_url)
        self.assertEqual(response.status_code, 404)

    def test_detail_view_accessible_by_admin(self):
        self.client.login(username='quote_detail_admin', password='password123')
        response = self.client.get(self.quote1_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(self.quote1.quote_id)
        self.assertContains(response, self.quote1.quote_id)

    def test_detail_view_accessible_by_manager(self):
        self.client.login(username='quote_detail_manager', password='password123')
        response = self.client.get(self.quote1_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.quote1.quote_id)


# Deal Create View Tests
class DealCreateViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.test_user = create_user(
            username='deal_create_user',
            role=CustomUser.Roles.SALES
        )
        cls.test_account = Account.objects.create(
            name="Deal Create Account",
            assigned_to=cls.test_user
        )
        cls.test_contact = Contact.objects.create(
            last_name="Deal Create Contact",
            account=cls.test_account,
            assigned_to=cls.test_user
        )

    def setUp(self):
        self.client.login(username='deal_create_user', password='password123')
        self.create_url = reverse('sales_pipeline:deal-create')
        self.list_url = reverse('sales_pipeline:deal-list')

    def test_create_view_get_page_authenticated(self):
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sales_pipeline/deal_form.html')
        self.assertContains(response, 'Create New Deal')

    def test_create_view_redirects_if_not_logged_in(self):
        self.client.logout()
        response = self.client.get(self.create_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.create_url}')

    def test_create_deal_success_post(self):
        initial_deal_count = Deal.objects.count()
        close_date_str = (date.today() + timedelta(days=45)).strftime('%Y-%m-%d')
        deal_data = {
            'name': 'New Deal From Test',
            'account': self.test_account.pk,
            'primary_contact': self.test_contact.pk,
            'stage': Deal.StageChoices.QUALIFICATION,
            'amount': '5000.00',
            'currency': 'PHP',
            'close_date': close_date_str,
            'assigned_to': '',
            'description': 'Test description',
        }
        response = self.client.post(self.create_url, data=deal_data)

        self.assertRedirects(response, self.list_url)
        self.assertEqual(Deal.objects.count(), initial_deal_count + 1)

        new_deal = Deal.objects.latest('created_at')
        self.assertEqual(new_deal.name, 'New Deal From Test')
        self.assertEqual(new_deal.account, self.test_account)
        self.assertEqual(new_deal.primary_contact, self.test_contact)
        self.assertEqual(new_deal.stage, Deal.StageChoices.QUALIFICATION)
        self.assertEqual(new_deal.created_by, self.test_user)
        self.assertEqual(new_deal.assigned_to, self.test_user)
        expected_probability = Deal.STAGE_PROBABILITY_MAP.get(
            Deal.StageChoices.QUALIFICATION
        )
        self.assertEqual(new_deal.probability, expected_probability)
        self.assertIsNotNone(new_deal.deal_id)
        current_year_str = timezone.now().strftime('%y')
        self.assertTrue(re.match(rf"D{current_year_str}-\d{{5}}", new_deal.deal_id))

    def test_create_deal_missing_required_field(self):
        initial_deal_count = Deal.objects.count()
        deal_data = {
            'account': self.test_account.pk,
            'currency': 'PHP',
        }
        response = self.client.post(self.create_url, data=deal_data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Deal.objects.count(), initial_deal_count)
        form_in_context = response.context.get('form')
        self.assertIsNotNone(form_in_context)
        self.assertFormError(form_in_context, 'name', 'This field is required.')
        self.assertFormError(form_in_context, 'stage', 'This field is required.')
        self.assertFormError(form_in_context, 'amount', 'This field is required.')
        self.assertFormError(form_in_context, 'close_date', 'This field is required.')
        self.assertTemplateUsed(response, 'sales_pipeline/deal_form.html')

    def test_create_view_initial_data_from_query_params(self):
        response = self.client.get(
            self.create_url,
            {'account': self.test_account.pk, 'contact': self.test_contact.pk}
        )
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertEqual(form.initial.get('account'), self.test_account)
        self.assertEqual(form.initial.get('primary_contact'), self.test_contact)

    def test_create_view_invalid_account_query_param(self):
        response = self.client.get(self.create_url, {'account': 9999})
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertNotIn('account', form.initial)
        self.assertContains(response, "Invalid Account specified.")


# Quote Create View Tests
class QuoteCreateViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.test_user = create_user(
            username='quote_create_user',
            role=CustomUser.Roles.SALES
        )
        cls.test_account = Account.objects.create(
            name="Quote Create Account",
            assigned_to=cls.test_user
        )
        cls.test_deal = Deal.objects.create(
            name="Quote Create Deal",
            account=cls.test_account,
            stage=Deal.StageChoices.PROPOSAL,
            amount=100,
            close_date=date.today(),
            assigned_to=cls.test_user
        )
        cls.test_contact = Contact.objects.create(
            last_name="Quote Create Contact",
            account=cls.test_account,
            assigned_to=cls.test_user
        )

    def setUp(self):
        self.client.login(username='quote_create_user', password='password123')
        self.create_url = reverse('sales_pipeline:quote-create')
        self.list_url = reverse('sales_pipeline:quote-list')

    def test_create_view_get_page_authenticated(self):
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sales_pipeline/quote_form.html')
        self.assertContains(response, 'Create New Quote')
        self.assertEqual(response.context['form'].initial.get('assigned_to'), self.test_user)

    def test_create_view_redirects_if_not_logged_in(self):
        self.client.logout()
        response = self.client.get(self.create_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.create_url}')

    def test_create_quote_success_post(self):
        initial_quote_count = Quote.objects.count()
        presented_date_str = date.today().strftime('%Y-%m-%d')
        quote_data = {
            'deal': self.test_deal.pk,
            'contact': self.test_contact.pk,
            'status': Quote.StatusChoices.PRESENTED,
            'total_amount': '1234.56',
            'presented_date': presented_date_str,
            'validity_days': 45,
            'assigned_to': self.test_user.pk,
            'notes': 'Test quote notes',
        }
        response = self.client.post(self.create_url, data=quote_data)

        self.assertRedirects(response, self.list_url)
        self.assertEqual(Quote.objects.count(), initial_quote_count + 1)

        new_quote = Quote.objects.latest('created_at')
        self.assertEqual(new_quote.deal, self.test_deal)
        self.assertEqual(new_quote.contact, self.test_contact)
        self.assertEqual(new_quote.status, Quote.StatusChoices.PRESENTED)
        self.assertEqual(new_quote.created_by, self.test_user)
        self.assertEqual(new_quote.assigned_to, self.test_user)
        self.assertEqual(new_quote.account, self.test_deal.account)
        self.assertIsNotNone(new_quote.quote_id)
        current_year_str = timezone.now().strftime('%y')
        self.assertTrue(re.match(rf"Q{current_year_str}-\d{{5}}", new_quote.quote_id))

    def test_create_quote_missing_required_field(self):
        initial_quote_count = Quote.objects.count()
        quote_data = {
            'contact': self.test_contact.pk,
            'status': Quote.StatusChoices.DRAFT,
        }
        response = self.client.post(self.create_url, data=quote_data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Quote.objects.count(), initial_quote_count)
        form_in_context = response.context.get('form')
        self.assertIsNotNone(form_in_context)
        self.assertFormError(form_in_context, 'deal', 'This field is required.')
        self.assertTemplateUsed(response, 'sales_pipeline/quote_form.html')

    def test_create_quote_invalid_deal_id(self):
        initial_quote_count = Quote.objects.count()
        presented_date_str = date.today().strftime('%Y-%m-%d')
        quote_data = {
            'deal': 9999,  # Non-existent deal ID
            'contact': self.test_contact.pk,
            'status': Quote.StatusChoices.PRESENTED,
            'total_amount': '1234.56',
            'presented_date': presented_date_str,
            'validity_days': 45,
            'assigned_to': self.test_user.pk,
            'notes': 'Test quote notes',
        }
        response = self.client.post(self.create_url, data=quote_data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Quote.objects.count(), initial_quote_count)
        self.assertContains(response, "Select a valid choice. That choice is not one of the available choices.")
        self.assertTemplateUsed(response, 'sales_pipeline/quote_form.html')

    def test_create_quote_deal_no_account(self):
        initial_quote_count = Quote.objects.count()
        presented_date_str = date.today().strftime('%Y-%m-%d')
        quote_data = {
            'deal': self.test_deal.pk,
            'contact': self.test_contact.pk,
            'status': Quote.StatusChoices.PRESENTED,
            'total_amount': '1234.56',
            'presented_date': presented_date_str,
            'validity_days': 45,
            'assigned_to': self.test_user.pk,
            'notes': 'Test quote notes',
        }
        with patch.object(Deal, 'account', None):
            response = self.client.post(self.create_url, data=quote_data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Quote.objects.count(), initial_quote_count)
        self.assertContains(response, "Selected Deal must have an associated Account.")
        self.assertTemplateUsed(response, 'sales_pipeline/quote_form.html')


# Deal Update View Tests
class DealUpdateViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user(
            username='deal_update_owner',
            role=CustomUser.Roles.SALES
        )
        cls.other_user = create_user(
            username='deal_update_other',
            role=CustomUser.Roles.SALES
        )
        cls.admin_user = create_user(
            username='deal_update_admin',
            is_superuser=True
        )
        cls.account = Account.objects.create(
            name="Update Deal Account",
            assigned_to=cls.owner_user
        )
        cls.deal_to_update = Deal.objects.create(
            name="Update Test Deal",
            account=cls.account,
            stage=Deal.StageChoices.PROSPECTING,
            amount=Decimal('1000.00'),
            close_date=date.today(),
            assigned_to=cls.owner_user
        )
        cls.initial_probability = Deal.STAGE_PROBABILITY_MAP[
            Deal.StageChoices.PROSPECTING
        ]
        cls.update_url = reverse(
            'sales_pipeline:deal-update',
            kwargs={'pk': cls.deal_to_update.pk}
        )
        cls.list_url = reverse('sales_pipeline:deal-list')

    def test_update_view_get_page_as_owner(self):
        self.client.login(username='deal_update_owner', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sales_pipeline/deal_form.html')
        self.assertEqual(response.context['form'].initial['name'], self.deal_to_update.name)
        self.assertContains(response, 'Update Deal:')

    def test_update_view_get_permission_denied_for_other_user(self):
        self.client.login(username='deal_update_other', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 404)

    def test_update_deal_success_post_as_owner(self):
        self.client.login(username='deal_update_owner', password='password123')
        updated_name = "Updated Deal Name by Owner"
        updated_stage = Deal.StageChoices.PROPOSAL
        updated_amount = Decimal('9999.99')
        expected_probability = Deal.STAGE_PROBABILITY_MAP[updated_stage]

        deal_data = {
            'name': updated_name,
            'account': self.deal_to_update.account.pk,
            'stage': updated_stage,
            'amount': updated_amount,
            'currency': self.deal_to_update.currency,
            'close_date': self.deal_to_update.close_date.strftime('%Y-%m-%d'),
            'assigned_to': self.deal_to_update.assigned_to.pk,
            'description': 'Updated description',
        }
        response = self.client.post(self.update_url, data=deal_data)

        self.assertRedirects(response, self.list_url)
        self.deal_to_update.refresh_from_db()
        self.assertEqual(self.deal_to_update.name, updated_name)
        self.assertEqual(self.deal_to_update.stage, updated_stage)
        self.assertEqual(self.deal_to_update.amount, updated_amount)
        self.assertEqual(self.deal_to_update.probability, expected_probability)

    def test_update_deal_permission_denied_post_other_user(self):
        self.client.login(username='deal_update_other', password='password123')
        original_name = self.deal_to_update.name
        deal_data = {
            'name': 'Attempted Update Deal',
            'account': self.account.pk,
            'stage': Deal.StageChoices.QUALIFICATION,
            'amount': 1,
            'close_date': date.today()
        }
        response = self.client.post(self.update_url, data=deal_data)
        self.assertEqual(response.status_code, 404)
        self.deal_to_update.refresh_from_db()
        self.assertEqual(self.deal_to_update.name, original_name)


# Quote Update View Tests
class QuoteUpdateViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user(
            username='quote_update_owner_v2',
            role=CustomUser.Roles.SALES
        )
        cls.other_user = create_user(
            username='quote_update_other_v2',
            role=CustomUser.Roles.SALES
        )
        cls.admin_user = create_user(
            username='quote_update_admin_v2',
            is_superuser=True
        )
        cls.account1 = Account.objects.create(
            name="Update Quote Account 1",
            assigned_to=cls.owner_user
        )
        cls.account2 = Account.objects.create(
            name="Update Quote Account 2",
            assigned_to=cls.owner_user
        )
        cls.deal = Deal.objects.create(
            name="Update Quote Deal 1",
            account=cls.account1,
            stage=Deal.StageChoices.PROPOSAL,
            amount=500,
            close_date=date.today(),
            assigned_to=cls.owner_user
        )
        cls.other_deal = Deal.objects.create(
            name="Other Deal for Quote Update",
            account=cls.account2,
            stage=Deal.StageChoices.PROPOSAL,
            amount=600,
            close_date=date.today(),
            assigned_to=cls.owner_user
        )
        cls.quote_to_update = Quote.objects.create(
            deal=cls.deal,
            status=Quote.StatusChoices.DRAFT,
            total_amount=500,
            assigned_to=cls.owner_user,
            created_by=cls.owner_user
        )
        cls.quote_to_update.refresh_from_db()
        cls.update_url = reverse(
            'sales_pipeline:quote-update',
            kwargs={'pk': cls.quote_to_update.pk}
        )
        cls.list_url = reverse('sales_pipeline:quote-list')

    def test_update_view_get_page_as_owner(self):
        self.client.login(username='quote_update_owner_v2', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sales_pipeline/quote_form.html')
        self.assertEqual(
            response.context['form'].initial['status'],
            self.quote_to_update.status
        )
        self.assertContains(response, 'Update Quote:')
        self.assertContains(response, self.quote_to_update.quote_id)

    def test_update_view_get_permission_denied_for_other_user(self):
        self.client.login(username='quote_update_other_v2', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 404)

    def test_update_quote_success_post_as_owner(self):
        self.client.login(username='quote_update_owner_v2', password='password123')
        updated_status = Quote.StatusChoices.PRESENTED
        updated_amount = Decimal('550.00')
        original_account = self.quote_to_update.account

        quote_data = {
            'deal': self.other_deal.pk,
            'contact': '',
            'status': updated_status,
            'total_amount': updated_amount,
            'presented_date': date.today().strftime('%Y-%m-%d'),
            'validity_days': 60,
            'assigned_to': self.owner_user.pk,
            'notes': 'Updated notes',
        }
        response = self.client.post(self.update_url, data=quote_data)

        self.assertRedirects(response, self.list_url)
        self.quote_to_update.refresh_from_db()
        self.assertEqual(self.quote_to_update.status, updated_status)
        self.assertEqual(self.quote_to_update.total_amount, updated_amount)
        self.assertEqual(self.quote_to_update.validity_days, 60)
        self.assertEqual(self.quote_to_update.deal, self.other_deal)
        self.assertEqual(self.quote_to_update.account, self.other_deal.account)
        self.assertNotEqual(self.quote_to_update.account, original_account)

    def test_update_quote_missing_required_field(self):
        self.client.login(username='quote_update_owner_v2', password='password123')
        initial_status = self.quote_to_update.status
        quote_data = {
            'contact': '',
            'status': Quote.StatusChoices.PRESENTED,
            'total_amount': '550.00',
        }
        response = self.client.post(self.update_url, data=quote_data)

        self.assertEqual(response.status_code, 200)
        self.quote_to_update.refresh_from_db()
        self.assertEqual(self.quote_to_update.status, initial_status)
        form_in_context = response.context.get('form')
        self.assertIsNotNone(form_in_context)
        self.assertFormError(form_in_context, 'deal', 'This field is required.')
        self.assertTemplateUsed(response, 'sales_pipeline/quote_form.html')

    def test_update_quote_invalid_deal_id(self):
        self.client.login(username='quote_update_owner_v2', password='password123')
        initial_status = self.quote_to_update.status
        quote_data = {
            'deal': 9999,  # Non-existent deal ID
            'contact': '',
            'status': Quote.StatusChoices.PRESENTED,
            'total_amount': '550.00',
            'presented_date': date.today().strftime('%Y-%m-%d'),
            'validity_days': 60,
            'assigned_to': self.owner_user.pk,
            'notes': 'Updated notes',
        }
        response = self.client.post(self.update_url, data=quote_data)

        self.assertEqual(response.status_code, 200)
        self.quote_to_update.refresh_from_db()
        self.assertEqual(self.quote_to_update.status, initial_status)
        self.assertContains(response, "Select a valid choice. That choice is not one of the available choices.")
        self.assertTemplateUsed(response, 'sales_pipeline/quote_form.html')

    def test_update_quote_deal_no_account(self):
        self.client.login(username='quote_update_owner_v2', password='password123')
        initial_status = self.quote_to_update.status
        quote_data = {
            'deal': self.other_deal.pk,
            'contact': '',
            'status': Quote.StatusChoices.PRESENTED,
            'total_amount': '550.00',
            'presented_date': date.today().strftime('%Y-%m-%d'),
            'validity_days': 60,
            'assigned_to': self.owner_user.pk,
            'notes': 'Updated notes',
        }
        with patch.object(Deal, 'account', None):
            response = self.client.post(self.update_url, data=quote_data)

        self.assertEqual(response.status_code, 200)
        self.quote_to_update.refresh_from_db()
        self.assertEqual(self.quote_to_update.status, initial_status)
        self.assertContains(response, "A valid Deal must be selected.")
        self.assertTemplateUsed(response, 'sales_pipeline/quote_form.html')


# Deal Delete View Tests
class DealDeleteViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user(
            username='deal_delete_owner',
            role=CustomUser.Roles.SALES
        )
        cls.other_user = create_user(
            username='deal_delete_other',
            role=CustomUser.Roles.SALES
        )
        cls.admin_user = create_user(
            username='deal_delete_admin',
            is_superuser=True
        )
        cls.account = Account.objects.create(
            name="Delete Deal Account",
            assigned_to=cls.owner_user
        )
        cls.deal_to_delete = Deal.objects.create(
            name="Delete Test Deal",
            account=cls.account,
            stage=Deal.StageChoices.PROSPECTING,
            amount=1000,
            close_date=date.today(),
            assigned_to=cls.owner_user,
            created_by=cls.owner_user
        )
        cls.delete_url = reverse(
            'sales_pipeline:deal-delete',
            kwargs={'pk': cls.deal_to_delete.pk}
        )
        cls.list_url = reverse('sales_pipeline:deal-list')

    def test_delete_view_redirects_if_not_logged_in(self):
        response = self.client.get(self.delete_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.delete_url}')

    def test_delete_view_get_page_as_owner(self):
        self.client.login(username='deal_delete_owner', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sales_pipeline/deal_confirm_delete.html')
        self.assertContains(response, self.deal_to_delete.name)

    def test_delete_deal_success_post_as_owner(self):
        self.client.login(username='deal_delete_owner', password='password123')
        initial_deal_count = Deal.objects.count()
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(Deal.objects.count(), initial_deal_count - 1)
        self.assertFalse(Deal.objects.filter(pk=self.deal_to_delete.pk).exists())

    def test_delete_view_permission_denied_for_other_user(self):
        self.client.login(username='deal_delete_other', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 404)

    def test_delete_deal_accessible_by_admin(self):
        self.client.login(username='deal_delete_admin', password='password123')
        initial_deal_count = Deal.objects.count()
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(Deal.objects.count(), initial_deal_count - 1)
        self.assertFalse(Deal.objects.filter(pk=self.deal_to_delete.pk).exists())


# Quote Delete View Tests
class QuoteDeleteViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user(
            username='quote_delete_owner',
            role=CustomUser.Roles.SALES
        )
        cls.other_user = create_user(
            username='quote_delete_other',
            role=CustomUser.Roles.SALES
        )
        cls.admin_user = create_user(
            username='quote_delete_admin',
            is_superuser=True
        )
        cls.manager_user = create_user(
            'quote_delete_manager',
            role=CustomUser.Roles.MANAGER
        )
        cls.t1 = Territory.objects.create(name="Quote Delete Territory")
        cls.manager_user.managed_territories.add(cls.t1)
        cls.account = Account.objects.create(
            name="Delete Quote Account",
            territory=cls.t1,
            assigned_to=cls.owner_user
        )
        cls.deal = Deal.objects.create(
            name="Delete Quote Deal",
            account=cls.account,
            stage=Deal.StageChoices.PROPOSAL,
            amount=500,
            close_date=date.today(),
            assigned_to=cls.owner_user
        )
        cls.quote_to_delete = Quote.objects.create(
            deal=cls.deal,
            status=Quote.StatusChoices.DRAFT,
            total_amount=500,
            assigned_to=cls.owner_user,
            created_by=cls.owner_user
        )
        cls.quote_to_delete.refresh_from_db()
        cls.delete_url = reverse(
            'sales_pipeline:quote-delete',
            kwargs={'pk': cls.quote_to_delete.pk}
        )
        cls.list_url = reverse('sales_pipeline:quote-list')

    def test_delete_view_redirects_if_not_logged_in(self):
        response = self.client.get(self.delete_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.delete_url}')

    def test_delete_view_get_page_as_owner(self):
        self.client.login(username='quote_delete_owner', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sales_pipeline/quote_confirm_delete.html')
        self.assertContains(response, self.quote_to_delete.quote_id)

    def test_delete_quote_success_post_as_owner(self):
        self.client.login(username='quote_delete_owner', password='password123')
        initial_quote_count = Quote.objects.count()
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(Quote.objects.count(), initial_quote_count - 1)
        self.assertFalse(Quote.objects.filter(pk=self.quote_to_delete.pk).exists())

    def test_delete_view_permission_denied_for_other_user(self):
        self.client.login(username='quote_delete_other', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 404)

    def test_delete_quote_accessible_by_admin(self):
        self.client.login(username='quote_delete_admin', password='password123')
        initial_quote_count = Quote.objects.count()
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(Quote.objects.count(), initial_quote_count - 1)
        self.assertFalse(Quote.objects.filter(pk=self.quote_to_delete.pk).exists())

    def test_delete_quote_accessible_by_manager(self):
        self.client.login(username='quote_delete_manager', password='password123')
        initial_quote_count = Quote.objects.count()
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(Quote.objects.count(), initial_quote_count - 1)
        self.assertFalse(Quote.objects.filter(pk=self.quote_to_delete.pk).exists())


# Deal Autocomplete View Tests
class DealAutocompleteTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.sales_user = create_user(
            'deal_autocomplete_sales',
            role=CustomUser.Roles.SALES
        )
        cls.manager_user = create_user(
            'deal_autocomplete_manager',
            role=CustomUser.Roles.MANAGER
        )
        cls.admin_user = create_user(
            'deal_autocomplete_admin',
            is_superuser=True
        )
        cls.t1 = Territory.objects.create(name="Autocomplete Territory")
        cls.manager_user.managed_territories.add(cls.t1)
        cls.account1 = Account.objects.create(
            name="Autocomplete Account 1",
            territory=cls.t1,
            assigned_to=cls.sales_user
        )
        cls.account2 = Account.objects.create(
            name="Autocomplete Account 2",
            assigned_to=cls.manager_user
        )
        cls.deal1 = Deal.objects.create(
            name="Sales Deal Test",
            account=cls.account1,
            stage=Deal.StageChoices.PROPOSAL,
            amount=1000,
            close_date=date.today(),
            assigned_to=cls.sales_user
        )
        cls.deal2 = Deal.objects.create(
            name="Manager Deal Test",
            account=cls.account2,
            stage=Deal.StageChoices.PROPOSAL,
            amount=2000,
            close_date=date.today(),
            assigned_to=cls.manager_user
        )
        cls.autocomplete_url = reverse('sales_pipeline:deal-autocomplete')

    def test_autocomplete_redirects_if_not_logged_in(self):
        response = self.client.get(self.autocomplete_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.autocomplete_url}')

    def test_sales_user_sees_own_deals(self):
        self.client.login(username='deal_autocomplete_sales', password='password123')
        response = self.client.get(self.autocomplete_url, {'q': 'Test'})
        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['text'], str(self.deal1))

    def test_manager_sees_team_deals(self):
        self.client.login(
            username='deal_autocomplete_manager',
            password='password123'
        )
        response = self.client.get(self.autocomplete_url, {'q': 'Test'})
        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertEqual(len(results), 2)
        deal_names = {result['text'] for result in results}
        self.assertIn(str(self.deal1), deal_names)
        self.assertIn(str(self.deal2), deal_names)

    def test_admin_sees_all_deals(self):
        self.client.login(username='deal_autocomplete_admin', password='password123')
        response = self.client.get(self.autocomplete_url, {'q': 'Test'})
        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertEqual(len(results), 2)
        deal_names = {result['text'] for result in results}
        self.assertIn(str(self.deal1), deal_names)
        self.assertIn(str(self.deal2), deal_names)


# Deal Export View Tests
class DealExportViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = create_user('deal_export_admin', is_superuser=True)
        cls.sales_user = create_user(
            'deal_export_sales',
            role=CustomUser.Roles.SALES
        )
        cls.account = Account.objects.create(
            name="Export Deal Account",
            assigned_to=cls.sales_user
        )
        cls.deal = Deal.objects.create(
            name="Export Test Deal",
            account=cls.account,
            stage=Deal.StageChoices.PROPOSAL,
            amount=1000,
            close_date=date.today(),
            assigned_to=cls.sales_user,
            created_by=cls.sales_user
        )
        cls.export_url = reverse('sales_pipeline:deal-export')

    def test_export_view_redirects_if_not_logged_in(self):
        response = self.client.get(self.export_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.export_url}')

    def test_export_view_forbidden_for_non_admin(self):
        self.client.login(username='deal_export_sales', password='password123')
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 403)

    def test_export_view_success_for_admin(self):
        self.client.login(username='deal_export_admin', password='password123')
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        self.assertEqual(
            response['Content-Disposition'],
            'attachment; filename="deals_export.xlsx"'
        )

        # Parse the Excel file
        workbook = openpyxl.load_workbook(io.BytesIO(response.content))
        worksheet = workbook['Deals']
        # Check headers (row 1)
        headers = [cell.value for cell in worksheet[1]]
        expected_headers = [
            "Deal ID", "Name", "Account", "Primary Contact", "Stage", "Amount",
            "Currency", "Close Date", "Probability (%)", "Description",
            "Assigned To", "Created By", "Created At", "Updated At"
        ]
        self.assertEqual(headers, expected_headers)
        # Check data (row 2)
        data_row = [cell.value for cell in worksheet[2]]
        self.assertEqual(data_row[1], "Export Test Deal")  # Name column
        self.assertEqual(data_row[2], "Export Deal Account")  # Account column
        self.assertEqual(data_row[4], Deal.StageChoices.PROPOSAL.label)  # Stage display value


# Quote Export View Tests
class QuoteExportViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = create_user('quote_export_admin', is_superuser=True)
        cls.sales_user = create_user(
            'quote_export_sales',
            role=CustomUser.Roles.SALES
        )
        cls.account = Account.objects.create(
            name="Export Quote Account",
            assigned_to=cls.sales_user
        )
        cls.deal = Deal.objects.create(
            name="Export Quote Deal",
            account=cls.account,
            stage=Deal.StageChoices.PROPOSAL,
            amount=500,
            close_date=date.today(),
            assigned_to=cls.sales_user
        )
        cls.quote = Quote.objects.create(
            deal=cls.deal,
            status=Quote.StatusChoices.DRAFT,
            total_amount=500,
            assigned_to=cls.sales_user,
            created_by=cls.sales_user
        )
        cls.quote.refresh_from_db()
        cls.export_url = reverse('sales_pipeline:quote-export')

    def test_export_view_redirects_if_not_logged_in(self):
        response = self.client.get(self.export_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.export_url}')

    def test_export_view_forbidden_for_non_admin(self):
        self.client.login(username='quote_export_sales', password='password123')
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 403)

    def test_export_view_success_for_admin(self):
        self.client.login(username='quote_export_admin', password='password123')
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        self.assertEqual(
            response['Content-Disposition'],
            'attachment; filename="quotes_export.xlsx"'
        )

        # Parse the Excel file
        workbook = openpyxl.load_workbook(io.BytesIO(response.content))
        worksheet = workbook['Quotes']
        # Check headers (row 1)
        headers = [cell.value for cell in worksheet[1]]
        expected_headers = [
            "Quote ID", "Account", "Deal ID", "Contact", "Status", "Total Amount",
            "Presented Date", "Validity (Days)", "Expiry Date", "Notes",
            "Assigned To", "Created By", "Created At", "Updated At"
        ]
        self.assertEqual(headers, expected_headers)
        # Check data (row 2)
        data_row = [cell.value for cell in worksheet[2]]
        self.assertEqual(data_row[0], self.quote.quote_id)  # Quote ID column
        self.assertEqual(data_row[1], "Export Quote Account")  # Account column
        self.assertEqual(data_row[4], Quote.StatusChoices.DRAFT.label)  # Status display value