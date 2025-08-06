from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError
from users.models import CustomUser
from sales_territories.models import Territory
from crm_entities.models import Account, Contact
from sales_pipeline.models import Deal
from ..models import Call, Task, Meeting


# Helper function
def create_user(username, role=CustomUser.Roles.SALES, territory=None, is_superuser=False):
    """ Creates a user with specified role and territory """
    if is_superuser:
        return CustomUser.objects.create_superuser(
            username=username,
            password="password123",
            email=f"{username}@example.com",
            role=CustomUser.Roles.ADMIN
        )
    return CustomUser.objects.create_user(
        username=username,
        password="password123",
        role=role,
        territory=territory,
        email=f"{username}@example.com"
    )


class CallListViewPermissionTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = create_user('call_list_admin', is_superuser=True)
        cls.manager_user = create_user('call_list_manager', role=CustomUser.Roles.MANAGER)
        cls.t1 = Territory.objects.create(name="Call Test Territory 1")
        cls.t2 = Territory.objects.create(name="Call Test Territory 2")
        cls.sales_user1 = create_user('call_list_sales1', role=CustomUser.Roles.SALES, territory=cls.t1)
        cls.sales_user2 = create_user('call_list_sales2', role=CustomUser.Roles.SALES, territory=cls.t2)
        cls.empty_sales_user = create_user('call_list_empty_sales', role=CustomUser.Roles.SALES, territory=cls.t2)
        cls.manager_user.managed_territories.add(cls.t1)

        cls.account1 = Account.objects.create(name="Call Account 1", territory=cls.t1, assigned_to=cls.sales_user1)
        cls.account2 = Account.objects.create(name="Call Account 2", territory=cls.t2, assigned_to=cls.sales_user2)
        cls.account_mgr = Account.objects.create(name="Call Account Mgr", territory=cls.t1, assigned_to=cls.manager_user)

        cls.call1 = Call.objects.create(
            subject="Sales1 Call",
            status='PLANNED',
            direction='OUTGOING',
            duration_minutes=60,
            created_by=cls.sales_user1,
            assigned_to=cls.sales_user1,
            related_to_account=cls.account1
        )
        cls.call2 = Call.objects.create(
            subject="Sales2 Call",
            status='HELD',
            direction='INCOMING',
            duration_minutes=30,
            created_by=cls.sales_user2,
            assigned_to=cls.sales_user2,
            related_to_account=cls.account2
        )
        cls.call_mgr = Call.objects.create(
            subject="Manager Call",
            status='PLANNED',
            direction='OUTGOING',
            duration_minutes=45,
            created_by=cls.manager_user,
            assigned_to=cls.manager_user,
            related_to_account=cls.account_mgr
        )

        cls.call_list_url = reverse('activities:call-list')

    def test_url_and_template(self):
        self.client.login(username='call_list_admin', password='password123')
        response = self.client.get(self.call_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/call_list.html')

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.call_list_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.call_list_url}')

    def test_admin_sees_all_calls(self):
        self.client.login(username='call_list_admin', password='password123')
        response = self.client.get(self.call_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['calls']), 3)

    def test_sales_user_sees_only_own_calls(self):
        self.client.login(username='call_list_sales1', password='password123')
        response = self.client.get(self.call_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['calls']), 1)
        self.assertEqual(response.context['calls'][0], self.call1)

    def test_manager_sees_own_team_and_territory_calls(self):
        self.client.login(username='call_list_manager', password='password123')
        response = self.client.get(self.call_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['calls']), 2)
        call_subjects = {c.subject for c in response.context['calls']}
        self.assertIn(self.call_mgr.subject, call_subjects)
        self.assertIn(self.call1.subject, call_subjects)

    def test_filter_by_status(self):
        self.client.login(username='call_list_admin', password='password123')
        response = self.client.get(self.call_list_url, {'status': 'HELD'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['calls']), 1)
        self.assertEqual(response.context['calls'][0], self.call2)

    def test_invalid_sort_param(self):
        self.client.login(username='call_list_admin', password='password123')
        response = self.client.get(self.call_list_url, {'sort': 'invalid_field'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sort_by'], 'call_time')
        self.assertEqual(response.context['direction'], 'desc')
    def test_empty_queryset(self):
        self.client.login(username='call_list_empty_sales', password='password123')
        response = self.client.get(self.call_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['calls']), 0)
    def test_filter_by_direction(self):
        self.client.login(username='call_list_admin', password='password123')
        response = self.client.get(self.call_list_url, {'direction': 'INCOMING'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['calls']), 1)
        self.assertEqual(response.context['calls'][0], self.call2)
    def test_filter_invalid_status(self):
        self.client.login(username='call_list_admin', password='password123')
        response = self.client.get(self.call_list_url, {'status': 'INVALID'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['calls']), 3)
    def test_direction_display(self):
        self.client.login(username='call_list_admin', password='password123')
        response = self.client.get(self.call_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.call1.get_direction_display())        
        
    def test_filter_empty_status(self):
        self.client.login(username='call_list_admin', password='password123')
        response = self.client.get(self.call_list_url, {'status': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['calls']), 3)
        
    def test_manager_multiple_territories(self):
        self.manager_user.managed_territories.add(self.t2)
        self.client.login(username='call_list_manager', password='password123')
        response = self.client.get(self.call_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['calls']), 3)
    def test_filter_invalid_related_account(self):
        self.client.login(username='call_list_admin', password='password123')
        response = self.client.get(self.call_list_url, {'related_to_account': 999})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['calls']), 3)
        
    def test_filter_no_related_account(self):
        self.client.login(username='call_list_admin', password='password123')
        response = self.client.get(self.call_list_url, {'related_to_account': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['calls']), 3)
        
    def test_filter_multiple_invalid(self):
        self.client.login(username='call_list_admin', password='password123')
        response = self.client.get(self.call_list_url, {'status': 'INVALID', 'direction': 'INVALID'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['calls']), 3)  # Filter ignores invalid values
        
    def test_form_invalid_assigned_to(self):
        self.client.login(username='call_list_admin', password='password123')
        initial_count = Call.objects.count()
        call_data = {
            'subject': 'Test Call',
            'status': 'PLANNED',
            'direction': 'OUTGOING',
            'duration_minutes': 30,
            'assigned_to': 999  # Invalid user ID
        }
        response = self.client.post(reverse('activities:call-create'), data=call_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Call.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'assigned_to', 'Select a valid choice. That choice is not one of the available choices.')
        
    def test_form_empty_subject(self):
        self.client.login(username='call_list_admin', password='password123')
        initial_count = Call.objects.count()
        call_data = {
            'subject': '',
            'status': 'PLANNED',
            'direction': 'OUTGOING',
            'duration_minutes': 30,
            'assigned_to': self.sales_user1.pk
        }
        response = self.client.post(reverse('activities:call-create'), data=call_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Call.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'subject', 'This field is required.')

    def test_filter_by_date_range(self):
        from django.utils import timezone
        self.client.login(username='call_list_admin', password='password123')
        Call.objects.create(
            subject='Old Call',
            status='COMPLETED',
            direction='OUTGOING',
            duration_minutes=30,
            created_at=timezone.now() - timezone.timedelta(days=10),
            assigned_to=self.sales_user1,
            created_by=self.sales_user1
        )
        response = self.client.get(self.call_list_url, {
            'created_at__gte': (timezone.now() - timezone.timedelta(days=5)).strftime('%Y-%m-%d'),
            'created_at__lte': timezone.now().strftime('%Y-%m-%d')
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['calls']), 4)  # Includes existing test data
                
    def test_form_invalid_subject(self):
        self.client.login(username='call_list_admin', password='password123')
        initial_count = Call.objects.count()
        call_data = {
            'subject': '',
            'status': 'PLANNED',
            'direction': 'OUTGOING',
            'duration_minutes': 30,
            'assigned_to': self.sales_user1.pk
        }
        response = self.client.post(reverse('activities:call-create'), data=call_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Call.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'subject', 'This field is required.')
        
    def test_filter_invalid_direction(self):
        self.client.login(username='call_list_admin', password='password123')
        response = self.client.get(self.call_list_url, {'direction': 'INVALID'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['calls']), 3)

    def test_form_invalid_duration(self):
        self.client.login(username='call_list_admin', password='password123')
        initial_count = Call.objects.count()
        call_data = {
            'subject': 'Test Call',
            'status': 'PLANNED',
            'direction': 'OUTGOING',
            'duration_minutes': -10,
            'assigned_to': self.sales_user1.pk
        }
        response = self.client.post(reverse('activities:call-create'), data=call_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Call.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'duration_minutes', 'Ensure this value is greater than or equal to 0.')
        



class CallDetailViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user('call_detail_owner', role=CustomUser.Roles.SALES)
        cls.other_user = create_user('call_detail_other', role=CustomUser.Roles.SALES)
        cls.admin_user = create_user('call_detail_admin', is_superuser=True)
        cls.account = Account.objects.create(name="Detail Call Account", assigned_to=cls.owner_user)
        cls.call = Call.objects.create(
            subject="Detail Test Call",
            status='PLANNED',
            direction='OUTGOING',
            call_time=timezone.now(),
            duration_minutes=60,
            created_by=cls.owner_user,
            assigned_to=cls.owner_user,
            related_to_account=cls.account
        )
        cls.call_detail_url = reverse('activities:call-detail', kwargs={'pk': cls.call.pk})

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.call_detail_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.call_detail_url}')

    def test_accessible_by_owner(self):
        self.client.login(username='call_detail_owner', password='password123')
        response = self.client.get(self.call_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/call_detail.html')

    def test_contains_call_details(self):
        self.client.login(username='call_detail_owner', password='password123')
        response = self.client.get(self.call_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.call.subject)
        self.assertEqual(response.context['call'], self.call)

    def test_permission_denied_for_other_user(self):
        self.client.login(username='call_detail_other', password='password123')
        response = self.client.get(self.call_detail_url)
        self.assertEqual(response.status_code, 404)

    def test_accessible_by_admin(self):
        self.client.login(username='call_detail_admin', password='password123')
        response = self.client.get(self.call_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.call.subject)


class CallCreateViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.test_user = create_user('call_create_user', role=CustomUser.Roles.SALES)
        cls.account = Account.objects.create(name="Call Create Account", assigned_to=cls.test_user)
        cls.contact = Contact.objects.create(
            last_name="Call Create Contact",
            account=cls.account,
            assigned_to=cls.test_user
        )
        cls.deal = Deal.objects.create(
            name="Call Create Deal",
            account=cls.account,
            stage=Deal.StageChoices.PROPOSAL,
            amount=1000,
            close_date=timezone.now().date(),
            assigned_to=cls.test_user
        )

    def setUp(self):
        self.client.login(username='call_create_user', password='password123')
        self.create_url = reverse('activities:call-create')
        self.list_url = reverse('activities:call-list')

    def test_get_page_authenticated(self):
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/call_form.html')
        self.assertContains(response, 'Log New Call')

    def test_redirect_if_not_logged_in(self):
        self.client.logout()
        response = self.client.get(self.create_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.create_url}')

    def test_create_call_success_post(self):
        initial_call_count = Call.objects.count()
        call_time_str = timezone.now().strftime('%Y-%m-%dT%H:%M')
        call_data = {
            'subject': 'New Test Call',
            'status': 'PLANNED',
            'direction': 'OUTGOING',

            'duration_minutes': 30,
            'related_to_account': self.account.pk,
            'related_to_contact': self.contact.pk,
            'related_to_deal': self.deal.pk,
            'assigned_to': self.test_user.pk,
            'notes': 'Test call notes'
        }
        response = self.client.post(self.create_url, data=call_data)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(Call.objects.count(), initial_call_count + 1)
        new_call = Call.objects.latest('created_at')
        self.assertEqual(new_call.subject, 'New Test Call')
        self.assertEqual(new_call.created_by, self.test_user)
        self.assertEqual(new_call.assigned_to, self.test_user)
        self.assertEqual(new_call.notes, 'Test call notes')

    def test_create_call_missing_required_field(self):
        initial_call_count = Call.objects.count()
        call_data = {
            'status': 'PLANNED',
            'direction': 'OUTGOING',
            'call_time': timezone.now().strftime('%Y-%m-%dT%H:%M')
        }
        response = self.client.post(self.create_url, data=call_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Call.objects.count(), initial_call_count)
        self.assertFormError(response.context['form'], 'subject', 'This field is required.')
        self.assertTemplateUsed(response, 'activities/call_form.html')

    def test_create_call_invalid_duration(self):
        initial_call_count = Call.objects.count()
        call_time_str = timezone.now().strftime('%Y-%m-%dT%H:%M')
        call_data = {
            'subject': 'Invalid Call',
            'status': 'PLANNED',
            'direction': 'OUTGOING',

            'duration_minutes': -10,
            'related_to_account': self.account.pk,
            'assigned_to': self.test_user.pk
        }
        response = self.client.post(self.create_url, data=call_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Call.objects.count(), initial_call_count)
        self.assertFormError(response.context['form'], 'duration_minutes', 'Ensure this value is greater than or equal to 0.')
        self.assertTemplateUsed(response, 'activities/call_form.html')


class CallUpdateViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user('call_update_owner', role=CustomUser.Roles.SALES)
        cls.other_user = create_user('call_update_other', role=CustomUser.Roles.SALES)
        cls.admin_user = create_user('call_update_admin', is_superuser=True)
        cls.account = Account.objects.create(name="Update Call Account", assigned_to=cls.owner_user)
        cls.call = Call.objects.create(
            subject="Update Test Call",
            status='PLANNED',
            direction='OUTGOING',
            duration_minutes=60,
            created_by=cls.owner_user,
            assigned_to=cls.owner_user,
            related_to_account=cls.account
        )
        cls.update_url = reverse('activities:call-update', kwargs={'pk': cls.call.pk})
        cls.list_url = reverse('activities:call-list')

    def test_get_page_as_owner(self):
        self.client.login(username='call_update_owner', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/call_form.html')
        self.assertEqual(response.context['form'].initial['subject'], self.call.subject)

    def test_permission_denied_for_other_user(self):
        self.client.login(username='call_update_other', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 404)

    def test_update_call_success_post(self):
        self.client.login(username='call_update_owner', password='password123')
        call_time_str = timezone.now().strftime('%Y-%m-%dT%H:%M')
        call_data = {
            'subject': 'Updated Test Call',
            'status': 'HELD',
            'direction': 'INCOMING',
            'duration_minutes': 45,
            'related_to_account': self.account.pk,
            'assigned_to': self.owner_user.pk,
            'notes': 'Updated call notes'
        }
        response = self.client.post(self.update_url, data=call_data)
        self.assertRedirects(response, self.list_url)
        self.call.refresh_from_db()
        self.assertEqual(self.call.subject, 'Updated Test Call')
        self.assertEqual(self.call.status, 'HELD')
        self.assertEqual(self.call.direction, 'INCOMING')
        self.assertEqual(self.call.duration_minutes, 45)
        self.assertEqual(self.call.notes, 'Updated call notes')

    def test_update_call_invalid_input(self):
        self.client.login(username='call_update_owner', password='password123')
        initial_status = self.call.status
        call_time_str = timezone.now().strftime('%Y-%m-%dT%H:%M')
        call_data = {
            'subject': '',
            'status': 'PLANNED',
            'direction': 'OUTGOING',
            'duration_minutes': 30,
            'related_to_account': self.account.pk,
            'assigned_to': self.owner_user.pk
        }
        response = self.client.post(self.update_url, data=call_data)
        self.assertEqual(response.status_code, 200)
        self.call.refresh_from_db()
        self.assertEqual(self.call.status, initial_status)
        self.assertFormError(response.context['form'], 'subject', 'This field is required.')
        self.assertTemplateUsed(response, 'activities/call_form.html')


class CallDeleteViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user('call_delete_owner', role=CustomUser.Roles.SALES)
        cls.other_user = create_user('call_delete_other', role=CustomUser.Roles.SALES)
        cls.admin_user = create_user('call_delete_admin', is_superuser=True)
        cls.account = Account.objects.create(name="Delete Call Account", assigned_to=cls.owner_user)
        cls.call = Call.objects.create(
            subject="Delete Test Call",
            status='PLANNED',
            direction='OUTGOING',
            call_time=timezone.now(),
            duration_minutes=60,
            created_by=cls.owner_user,
            assigned_to=cls.owner_user,
            related_to_account=cls.account
        )
        cls.delete_url = reverse('activities:call-delete', kwargs={'pk': cls.call.pk})
        cls.list_url = reverse('activities:call-list')

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.delete_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.delete_url}')

    def test_get_page_as_owner(self):
        self.client.login(username='call_delete_owner', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/call_confirm_delete.html')
        self.assertContains(response, self.call.subject)

    def test_delete_call_success_post(self):
        self.client.login(username='call_delete_owner', password='password123')
        initial_call_count = Call.objects.count()
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(Call.objects.count(), initial_call_count - 1)
        self.assertFalse(Call.objects.filter(pk=self.call.pk).exists())

    def test_permission_denied_for_other_user(self):
        self.client.login(username='call_delete_other', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 404)

    def test_delete_call_accessible_by_admin(self):
        self.client.login(username='call_delete_admin', password='password123')
        initial_call_count = Call.objects.count()
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(Call.objects.count(), initial_call_count - 1)
        self.assertFalse(Call.objects.filter(pk=self.call.pk).exists())


class TaskListViewPermissionTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = create_user('task_list_admin', is_superuser=True)
        cls.manager_user = create_user('task_list_manager', role=CustomUser.Roles.MANAGER)
        cls.t1 = Territory.objects.create(name="Task Test Territory 1")
        cls.t2 = Territory.objects.create(name="Task Test Territory 2")
        cls.sales_user1 = create_user('task_list_sales1', role=CustomUser.Roles.SALES, territory=cls.t1)
        cls.sales_user2 = create_user('task_list_sales2', role=CustomUser.Roles.SALES, territory=cls.t2)
        cls.empty_sales_user = create_user('task_list_empty_sales', role=CustomUser.Roles.SALES, territory=cls.t2)
        cls.manager_user.managed_territories.add(cls.t1)

        cls.account1 = Account.objects.create(name="Task Account 1", territory=cls.t1, assigned_to=cls.sales_user1)
        cls.account2 = Account.objects.create(name="Task Account 2", territory=cls.t2, assigned_to=cls.sales_user2)
        cls.account_mgr = Account.objects.create(name="Task Account Mgr", territory=cls.t1, assigned_to=cls.manager_user)

        cls.task1 = Task.objects.create(
            subject="Sales1 Task",
            status='NOT_STARTED',
            priority='NORMAL',
            due_date=timezone.now(),
            created_by=cls.sales_user1,
            assigned_to=cls.sales_user1,
            related_to_account=cls.account1
        )
        cls.task2 = Task.objects.create(
            subject="Sales2 Task",
            status='COMPLETED',
            priority='HIGH',
            due_date=timezone.now(),
            created_by=cls.sales_user2,
            assigned_to=cls.sales_user2,
            related_to_account=cls.account2
        )
        cls.task_mgr = Task.objects.create(
            subject="Manager Task",
            status='IN_PROGRESS',
            priority='LOW',
            due_date=timezone.now(),
            created_by=cls.manager_user,
            assigned_to=cls.manager_user,
            related_to_account=cls.account_mgr
        )

        cls.task_list_url = reverse('activities:task-list')

    def test_url_and_template(self):
        self.client.login(username='task_list_admin', password='password123')
        response = self.client.get(self.task_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/task_list.html')

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.task_list_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.task_list_url}')

    def test_admin_sees_all_tasks(self):
        self.client.login(username='task_list_admin', password='password123')
        response = self.client.get(self.task_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['tasks']), 3)

    def test_sales_user_sees_only_own_tasks(self):
        self.client.login(username='task_list_sales1', password='password123')
        response = self.client.get(self.task_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['tasks']), 1)
        self.assertEqual(response.context['tasks'][0], self.task1)

    def test_manager_sees_own_team_and_territory_tasks(self):
        self.client.login(username='task_list_manager', password='password123')
        response = self.client.get(self.task_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['tasks']), 2)
        task_subjects = {t.subject for t in response.context['tasks']}
        self.assertIn(self.task_mgr.subject, task_subjects)
        self.assertIn(self.task1.subject, task_subjects)

    def test_filter_by_status(self):
        self.client.login(username='task_list_admin', password='password123')
        response = self.client.get(self.task_list_url, {'status': 'COMPLETED'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['tasks']), 1)
        self.assertEqual(response.context['tasks'][0], self.task2)

    def test_invalid_sort_param(self):
        self.client.login(username='task_list_admin', password='password123')
        response = self.client.get(self.task_list_url, {'sort': 'invalid_field'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sort_by'], 'due_date')
        self.assertEqual(response.context['direction'], 'asc')

    def test_empty_queryset(self):
        self.client.login(username='task_list_empty_sales', password='password123')
        response = self.client.get(self.task_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['tasks']), 0)
    def test_filter_by_priority(self):
        self.client.login(username='task_list_admin', password='password123')
        response = self.client.get(self.task_list_url, {'priority': 'HIGH'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['tasks']), 1)
        self.assertEqual(response.context['tasks'][0], self.task2)
    def test_filter_multiple_criteria(self):
        self.client.login(username='task_list_admin', password='password123')
        response = self.client.get(self.task_list_url, {'status': 'COMPLETED', 'priority': 'HIGH'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['tasks']), 1)
        self.assertEqual(response.context['tasks'][0], self.task2)
    def test_str_display(self):
        self.client.login(username='task_list_admin', password='password123')
        response = self.client.get(self.task_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.task1))
        
    def test_task_str_in_detail(self):
        self.client.login(username='task_list_admin', password='password123')
        response = self.client.get(reverse('activities:task-detail', kwargs={'pk': self.task1.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.task1))
        
    def test_filter_due_date_range(self):
        self.client.login(username='task_list_admin', password='password123')
        response = self.client.get(self.task_list_url, {'due_date__gte': timezone.now().strftime('%Y-%m-%d')})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['tasks']), 3)
        
    def test_form_invalid_description(self):
        self.client.login(username='task_list_admin', password='password123')
        initial_count = Task.objects.count()
        task_data = {
            'subject': 'Test Task',
            'status': 'NOT_STARTED',
            'priority': 'NORMAL',
            'due_date': timezone.now().strftime('%Y-%m-%d'),
            'description': 'x' * 1001,
            'assigned_to': self.sales_user1.pk
        }
        response = self.client.post(reverse('activities:task-create'), data=task_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Task.objects.count(), initial_count + 1)
        
    def test_filter_invalid_due_date(self):
        self.client.login(username='task_list_admin', password='password123')
        response = self.client.get(self.task_list_url, {'due_date__gte': 'invalid'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['tasks']), 3)
    def test_form_invalid_priority(self):
        self.client.login(username='task_list_admin', password='password123')
        initial_count = Task.objects.count()
        task_data = {
            'subject': 'Test Task',
            'status': 'NOT_STARTED',
            'priority': 'INVALID',
            'due_date': timezone.now().strftime('%Y-%m-%d'),
            'description': 'Test description',
            'assigned_to': self.sales_user1.pk
        }
        response = self.client.post(reverse('activities:task-create'), data=task_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Task.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'priority', 'Select a valid choice. INVALID is not one of the available choices.')
        
    def test_filter_status_and_priority(self):
        self.client.login(username='task_list_admin', password='password123')
        response = self.client.get(self.task_list_url, {'status': 'COMPLETED', 'priority': 'HIGH'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['tasks']), 1)
        self.assertEqual(response.context['tasks'][0], self.task2)
    def test_form_empty_subject(self):
        self.client.login(username='task_list_admin', password='password123')
        initial_count = Task.objects.count()
        task_data = {
            'subject': '',
            'status': 'NOT_STARTED',
            'priority': 'NORMAL',
            'due_date': timezone.now().strftime('%Y-%m-%d'),
            'description': 'Test description',
            'assigned_to': self.sales_user1.pk
        }
        response = self.client.post(reverse('activities:task-create'), data=task_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Task.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'subject', 'This field is required.')
        
    def test_sales_no_tasks(self):
        # Ensure empty_sales_user exists
        if not CustomUser.objects.filter(username='empty_sales_user').exists():
            create_user('empty_sales_user', role=CustomUser.Roles.SALES, territory=self.t2)
        self.client.login(username='empty_sales_user', password='password123')
        response = self.client.get(self.task_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['tasks']), 0)
        self.assertContains(response, "No tasks found")
        
    def test_form_invalid_status(self):
        self.client.login(username='task_list_admin', password='password123')
        initial_count = Task.objects.count()
        task_data = {
            'subject': 'Test Task',
            'status': 'INVALID',
            'priority': 'NORMAL',
            'due_date': timezone.now().strftime('%Y-%m-%d'),
            'description': 'Test description',
            'assigned_to': self.sales_user1.pk
        }
        response = self.client.post(reverse('activities:task-create'), data=task_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Task.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'status', 'Select a valid choice. INVALID is not one of the available choices.')
        
    def test_task_str_rendering(self):
        self.client.login(username='task_list_admin', password='password123')
        response = self.client.get(self.task_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.task1))
        
def test_filter_by_invalid_due_date(self):
    self.client.login(username='task_list_admin', password='password123')
    response = self.client.get(self.task_list_url, {'due_date': 'invalid'})
    self.assertEqual(response.status_code, 200)
    self.assertEqual(len(response.context['tasks']), 3)  # Filter ignores invalid date
        
    def test_task_str_rendering(self):
        self.client.login(username='task_list_admin', password='password123')
        response = self.client.get(self.task_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.task1))
        
class TaskDetailViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user('task_detail_owner', role=CustomUser.Roles.SALES)
        cls.other_user = create_user('task_detail_other', role=CustomUser.Roles.SALES)
        cls.admin_user = create_user('task_detail_admin', is_superuser=True)
        cls.account = Account.objects.create(name="Detail Task Account", assigned_to=cls.owner_user)
        cls.task = Task.objects.create(
            subject="Detail Test Task",
            status='NOT_STARTED',
            priority='NORMAL',
            due_date=timezone.now(),
            created_by=cls.owner_user,
            assigned_to=cls.owner_user,
            related_to_account=cls.account
        )
        cls.task_detail_url = reverse('activities:task-detail', kwargs={'pk': cls.task.pk})

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.task_detail_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.task_detail_url}')

    def test_accessible_by_owner(self):
        self.client.login(username='task_detail_owner', password='password123')
        response = self.client.get(self.task_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/task_detail.html')

    def test_contains_task_details(self):
        self.client.login(username='task_detail_owner', password='password123')
        response = self.client.get(self.task_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.task.subject)
        self.assertEqual(response.context['task'], self.task)

    def test_permission_denied_for_other_user(self):
        self.client.login(username='task_detail_other', password='password123')
        response = self.client.get(self.task_detail_url)
        self.assertEqual(response.status_code, 404)

    def test_accessible_by_admin(self):
        self.client.login(username='task_detail_admin', password='password123')
        response = self.client.get(self.task_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.task.subject)


class TaskCreateViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.test_user = create_user('task_create_user', role=CustomUser.Roles.SALES)
        cls.account = Account.objects.create(name="Task Create Account", assigned_to=cls.test_user)
        cls.contact = Contact.objects.create(
            last_name="Task Create Contact",
            account=cls.account,
            assigned_to=cls.test_user
        )
        cls.deal = Deal.objects.create(
            name="Task Create Deal",
            account=cls.account,
            stage=Deal.StageChoices.PROPOSAL,
            amount=1000,
            close_date=timezone.now().date(),
            assigned_to=cls.test_user
        )

    def setUp(self):
        self.client.login(username='task_create_user', password='password123')
        self.create_url = reverse('activities:task-create')
        self.list_url = reverse('activities:task-list')

    def test_get_page_authenticated(self):
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/task_form.html')
        self.assertContains(response, 'Create New Task')

    def test_redirect_if_not_logged_in(self):
        self.client.logout()
        response = self.client.get(self.create_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.create_url}')

    def test_create_task_success_post(self):
        initial_task_count = Task.objects.count()
        due_date_str = timezone.now().strftime('%Y-%m-%d')
        task_data = {
            'subject': 'New Test Task',
            'status': 'NOT_STARTED',
            'priority': 'NORMAL',
            'due_date': due_date_str,
            'description': 'Test task description',
            'related_to_account': self.account.pk,
            'related_to_contact': self.contact.pk,
            'related_to_deal': self.deal.pk,
            'assigned_to': self.test_user.pk
        }
        response = self.client.post(self.create_url, data=task_data)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(Task.objects.count(), initial_task_count + 1)
        new_task = Task.objects.latest('created_at')
        self.assertEqual(new_task.subject, 'New Test Task')
        self.assertEqual(new_task.created_by, self.test_user)
        self.assertEqual(new_task.assigned_to, self.test_user)

    def test_create_task_missing_required_field(self):
        initial_task_count = Task.objects.count()
        task_data = {
            'status': 'NOT_STARTED',
            'priority': 'NORMAL',
            'due_date': timezone.now().strftime('%Y-%m-%dT%H:%M')
        }
        response = self.client.post(self.create_url, data=task_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Task.objects.count(), initial_task_count)
        self.assertFormError(response.context['form'], 'subject', 'This field is required.')
        self.assertTemplateUsed(response, 'activities/task_form.html')

    def test_create_task_invalid_due_date(self):
        initial_task_count = Task.objects.count()
        task_data = {
            'subject': 'Invalid Task',
            'status': 'NOT_STARTED',
            'priority': 'NORMAL',
            'due_date': 'invalid_date',
            'related_to_account': self.account.pk,
            'assigned_to': self.test_user.pk
        }
        response = self.client.post(self.create_url, data=task_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Task.objects.count(), initial_task_count)
        self.assertFormError(response.context['form'], 'due_date', 'Enter a valid date.')
        self.assertTemplateUsed(response, 'activities/task_form.html')


class TaskUpdateViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user('task_update_owner', role=CustomUser.Roles.SALES)
        cls.other_user = create_user('task_update_other', role=CustomUser.Roles.SALES)
        cls.admin_user = create_user('task_update_admin', is_superuser=True)
        cls.account = Account.objects.create(name="Update Task Account", assigned_to=cls.owner_user)
        cls.task = Task.objects.create(
            subject="Update Test Task",
            status='NOT_STARTED',
            priority='NORMAL',
            due_date=timezone.now(),
            created_by=cls.owner_user,
            assigned_to=cls.owner_user,
            related_to_account=cls.account
        )
        cls.update_url = reverse('activities:task-update', kwargs={'pk': cls.task.pk})
        cls.list_url = reverse('activities:task-list')

    def test_get_page_as_owner(self):
        self.client.login(username='task_update_owner', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/task_form.html')
        self.assertEqual(response.context['form'].initial['subject'], self.task.subject)

    def test_permission_denied_for_other_user(self):
        self.client.login(username='task_update_other', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 404)

    def test_update_task_success_post(self):
        self.client.login(username='task_update_owner', password='password123')
        due_date_str = timezone.now().strftime('%Y-%m-%d')
        task_data = {
            'subject': 'Updated Test Task',
            'status': 'COMPLETED',
            'priority': 'HIGH',
            'due_date': due_date_str,
            'description': 'Updated task description',
            'related_to_account': self.account.pk,
            'assigned_to': self.owner_user.pk
        }
        response = self.client.post(self.update_url, data=task_data)
        self.assertRedirects(response, self.list_url)
        self.task.refresh_from_db()
        self.assertEqual(self.task.subject, 'Updated Test Task')
        self.assertEqual(self.task.status, 'COMPLETED')
        self.assertEqual(self.task.priority, 'HIGH')

    def test_update_task_invalid_input(self):
        self.client.login(username='task_update_owner', password='password123')
        initial_status = self.task.status
        due_date_str = timezone.now().strftime('%Y-%m-%dT%H:%M')
        task_data = {
            'subject': '',
            'status': 'NOT_STARTED',
            'priority': 'NORMAL',
            'due_date': due_date_str,
            'related_to_account': self.account.pk,
            'assigned_to': self.owner_user.pk
        }
        response = self.client.post(self.update_url, data=task_data)
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, initial_status)
        self.assertFormError(response.context['form'], 'subject', 'This field is required.')
        self.assertTemplateUsed(response, 'activities/task_form.html')


class TaskDeleteViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user('task_delete_owner', role=CustomUser.Roles.SALES)
        cls.other_user = create_user('task_delete_other', role=CustomUser.Roles.SALES)
        cls.admin_user = create_user('task_delete_admin', is_superuser=True)
        cls.account = Account.objects.create(name="Delete Task Account", assigned_to=cls.owner_user)
        cls.task = Task.objects.create(
            subject="Delete Test Task",
            status='NOT_STARTED',
            priority='NORMAL',
            due_date=timezone.now(),
            created_by=cls.owner_user,
            assigned_to=cls.owner_user,
            related_to_account=cls.account
        )
        cls.delete_url = reverse('activities:task-delete', kwargs={'pk': cls.task.pk})
        cls.list_url = reverse('activities:task-list')

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.delete_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.delete_url}')

    def test_get_page_as_owner(self):
        self.client.login(username='task_delete_owner', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/task_confirm_delete.html')
        self.assertContains(response, self.task.subject)

    def test_delete_task_success_post(self):
        self.client.login(username='task_delete_owner', password='password123')
        initial_task_count = Task.objects.count()
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(Task.objects.count(), initial_task_count - 1)
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())

    def test_permission_denied_for_other_user(self):
        self.client.login(username='task_delete_other', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 404)

    def test_delete_task_accessible_by_admin(self):
        self.client.login(username='task_delete_admin', password='password123')
        initial_task_count = Task.objects.count()
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(Task.objects.count(), initial_task_count - 1)
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())


class MeetingListViewPermissionTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = create_user('meeting_list_admin', is_superuser=True)
        cls.manager_user = create_user('meeting_list_manager', role=CustomUser.Roles.MANAGER)
        cls.t1 = Territory.objects.create(name="Meeting Test Territory 1")
        cls.t2 = Territory.objects.create(name="Meeting Test Territory 2")
        cls.sales_user1 = create_user('meeting_list_sales1', role=CustomUser.Roles.SALES, territory=cls.t1)
        cls.sales_user2 = create_user('meeting_list_sales2', role=CustomUser.Roles.SALES, territory=cls.t2)
        cls.empty_sales_user = create_user('meeting_list_empty_sales', role=CustomUser.Roles.SALES, territory=cls.t2)
        cls.manager_user.managed_territories.add(cls.t1)

        cls.account1 = Account.objects.create(name="Meeting Account 1", territory=cls.t1, assigned_to=cls.sales_user1)
        cls.account2 = Account.objects.create(name="Meeting Account 2", territory=cls.t2, assigned_to=cls.sales_user2)
        cls.account_mgr = Account.objects.create(name="Meeting Account Mgr", territory=cls.t1, assigned_to=cls.manager_user)

        cls.meeting1 = Meeting.objects.create(
            subject="Sales1 Meeting",
            status='PLANNED',
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
            location="Office A",
            created_by=cls.sales_user1,
            assigned_to=cls.sales_user1,
            related_to_account=cls.account1
        )
        cls.meeting2 = Meeting.objects.create(
            subject="Sales2 Meeting",
            status='HELD',
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
            location="Office B",
            created_by=cls.sales_user2,
            assigned_to=cls.sales_user2,
            related_to_account=cls.account2
        )
        cls.meeting_mgr = Meeting.objects.create(
            subject="Manager Meeting",
            status='PLANNED',
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
            location="Office C",
            created_by=cls.manager_user,
            assigned_to=cls.manager_user,
            related_to_account=cls.account_mgr
        )

        cls.meeting_list_url = reverse('activities:meeting-list')

    def test_url_and_template(self):
        self.client.login(username='meeting_list_admin', password='password123')
        response = self.client.get(self.meeting_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/meeting_list.html')

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.meeting_list_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.meeting_list_url}')

    def test_admin_sees_all_meetings(self):
        self.client.login(username='meeting_list_admin', password='password123')
        response = self.client.get(self.meeting_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['meetings']), 3)

    def test_sales_user_sees_only_own_meetings(self):
        self.client.login(username='meeting_list_sales1', password='password123')
        response = self.client.get(self.meeting_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['meetings']), 1)
        self.assertEqual(response.context['meetings'][0], self.meeting1)

    def test_manager_sees_own_team_and_territory_meetings(self):
        self.client.login(username='meeting_list_manager', password='password123')
        response = self.client.get(self.meeting_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['meetings']), 2)
        meeting_subjects = {m.subject for m in response.context['meetings']}
        self.assertIn(self.meeting_mgr.subject, meeting_subjects)
        self.assertIn(self.meeting1.subject, meeting_subjects)

    def test_filter_by_status(self):
        self.client.login(username='meeting_list_admin', password='password123')
        response = self.client.get(self.meeting_list_url, {'status': 'HELD'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['meetings']), 1)
        self.assertEqual(response.context['meetings'][0], self.meeting2)

    def test_invalid_sort_param(self):
        self.client.login(username='meeting_list_admin', password='password123')
        response = self.client.get(self.meeting_list_url, {'sort': 'invalid_field'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sort_by'], 'start_time')
        self.assertEqual(response.context['direction'], 'desc')

    def test_empty_queryset(self):
        self.client.login(username='meeting_list_empty_sales', password='password123')
        response = self.client.get(self.meeting_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['meetings']), 0)
        
    def test_filter_no_results(self):
        self.client.login(username='meeting_list_admin', password='password123')
        response = self.client.get(self.meeting_list_url, {'status': 'INVALID'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['meetings']), 3)
    def test_str_display(self):
        self.client.login(username='meeting_list_admin', password='password123')
        response = self.client.get(self.meeting_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.meeting1))
        
    def test_filter_empty_status(self):
        self.client.login(username='meeting_list_admin', password='password123')
        response = self.client.get(self.meeting_list_url, {'status': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['meetings']), 3)
        
    def test_filter_start_time_range(self):
        self.client.login(username='meeting_list_admin', password='password123')
        response = self.client.get(self.meeting_list_url, {'start_time__gte': timezone.now().strftime('%Y-%m-%d')})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['meetings']), 3)
        
    def test_filter_invalid_start_time(self):
        self.client.login(username='meeting_list_admin', password='password123')
        response = self.client.get(self.meeting_list_url, {'start_time__gte': 'invalid'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['meetings']), 3)  # Filter ignores invalid values
        
    def test_form_invalid_location(self):
        self.client.login(username='meeting_list_admin', password='password123')
        initial_count = Meeting.objects.count()
        meeting_data = {
            'subject': 'Test Meeting',
            'status': 'PLANNED',
            'start_time': timezone.now().strftime('%Y-%m-%d %H:%M'),
            'end_time': (timezone.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M'),
            'location': 'x' * 256,  # Exceeds max length
            'assigned_to': self.sales_user1.pk
        }
        response = self.client.post(reverse('activities:meeting-create'), data=meeting_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Meeting.objects.count(), initial_count)
        self.assertFormError(response.context['form'], 'location', 'Ensure this value has at most 255 characters (it has 256).')
        
    def test_filter_by_location(self):
        self.client.login(username='meeting_list_admin', password='password123')
        Meeting.objects.create(
            subject='Test Meeting',
            status='PLANNED',
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1),
            location='Conference Room A',
            assigned_to=self.sales_user1,
            created_by=self.sales_user1
        )
        response = self.client.get(self.meeting_list_url, {'location__icontains': 'Conference'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['meetings']), 4)  # Includes existing test data
        self.assertTrue(any(m.location == 'Conference Room A' for m in response.context['meetings']))
                
    def test_filter_invalid_status(self):
        self.client.login(username='meeting_list_admin', password='password123')
        response = self.client.get(self.meeting_list_url, {'status': 'INVALID'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['meetings']), 3)

    def test_manager_no_territory(self):
        self.manager_user.managed_territories.clear()
        self.client.login(username='meeting_list_manager', password='password123')
        response = self.client.get(self.meeting_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['meetings']), 1)
        self.assertEqual(response.context['meetings'][0], self.meeting_mgr)


class MeetingDetailViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user('meeting_detail_owner', role=CustomUser.Roles.SALES)
        cls.other_user = create_user('meeting_detail_other', role=CustomUser.Roles.SALES)
        cls.admin_user = create_user('meeting_detail_admin', is_superuser=True)
        cls.account = Account.objects.create(name="Detail Meeting Account", assigned_to=cls.owner_user)
        cls.meeting = Meeting.objects.create(
            subject="Detail Test Meeting",
            status='PLANNED',
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
            location="Office",
            created_by=cls.owner_user,
            assigned_to=cls.owner_user,
            related_to_account=cls.account
        )
        cls.meeting_detail_url = reverse('activities:meeting-detail', kwargs={'pk': cls.meeting.pk})

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.meeting_detail_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.meeting_detail_url}')

    def test_accessible_by_owner(self):
        self.client.login(username='meeting_detail_owner', password='password123')
        response = self.client.get(self.meeting_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/meeting_detail.html')

    def test_contains_meeting_details(self):
        self.client.login(username='meeting_detail_owner', password='password123')
        response = self.client.get(self.meeting_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.meeting.subject)
        self.assertEqual(response.context['meeting'], self.meeting)

    def test_permission_denied_for_other_user(self):
        self.client.login(username='meeting_detail_other', password='password123')
        response = self.client.get(self.meeting_detail_url)
        self.assertEqual(response.status_code, 404)

    def test_accessible_by_admin(self):
        self.client.login(username='meeting_detail_admin', password='password123')
        response = self.client.get(self.meeting_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.meeting.subject)


class MeetingCreateViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.test_user = create_user('meeting_create_user', role=CustomUser.Roles.SALES)
        cls.account = Account.objects.create(name="Meeting Create Account", assigned_to=cls.test_user)
        cls.contact = Contact.objects.create(
            last_name="Meeting Create Contact",
            account=cls.account,
            assigned_to=cls.test_user
        )
        cls.deal = Deal.objects.create(
            name="Meeting Create Deal",
            account=cls.account,
            stage=Deal.StageChoices.PROPOSAL,
            amount=1000,
            close_date=timezone.now().date(),
            assigned_to=cls.test_user
        )

    def setUp(self):
        self.client.login(username='meeting_create_user', password='password123')
        self.create_url = reverse('activities:meeting-create')
        self.list_url = reverse('activities:meeting-list')

    def test_get_page_authenticated(self):
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/meeting_form.html')
        self.assertContains(response, 'Schedule New Meeting')

    def test_redirect_if_not_logged_in(self):
        self.client.logout()
        response = self.client.get(self.create_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.create_url}')

    def test_create_meeting_success_post(self):
        initial_meeting_count = Meeting.objects.count()
        start_time_str = timezone.now().strftime('%Y-%m-%dT%H:%M')
        end_time_str = (timezone.now() + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
        meeting_data = {
            'subject': 'New Test Meeting',
            'status': 'PLANNED',
            'start_time': start_time_str,
            'end_time': end_time_str,
            'location': 'Office',
            'related_to_account': self.account.pk,
            'related_to_contact': self.contact.pk,
            'related_to_deal': self.deal.pk,
            'assigned_to': self.test_user.pk
        }
        response = self.client.post(self.create_url, data=meeting_data)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(Meeting.objects.count(), initial_meeting_count + 1)
        new_meeting = Meeting.objects.latest('created_at')
        self.assertEqual(new_meeting.subject, 'New Test Meeting')
        self.assertEqual(new_meeting.created_by, self.test_user)
        self.assertEqual(new_meeting.assigned_to, self.test_user)

    def test_create_meeting_missing_required_field(self):
        initial_meeting_count = Meeting.objects.count()
        meeting_data = {
            'status': 'PLANNED',
            'start_time': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'end_time': (timezone.now() + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
        }
        response = self.client.post(self.create_url, data=meeting_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Meeting.objects.count(), initial_meeting_count)
        self.assertFormError(response.context['form'], 'subject', 'This field is required.')
        self.assertTemplateUsed(response, 'activities/meeting_form.html')

    def test_create_meeting_invalid_time(self):
        initial_meeting_count = Meeting.objects.count()
        meeting_data = {
            'subject': 'Invalid Meeting',
            'status': 'PLANNED',
            'start_time': 'invalid_time',
            'end_time': (timezone.now() + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
            'location': 'Office',
            'related_to_account': self.account.pk,
            'assigned_to': self.test_user.pk
        }
        response = self.client.post(self.create_url, data=meeting_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Meeting.objects.count(), initial_meeting_count)
        self.assertFormError(response.context['form'], 'start_time', 'Enter a valid date/time.')
        self.assertTemplateUsed(response, 'activities/meeting_form.html')


class MeetingUpdateViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user('meeting_update_owner', role=CustomUser.Roles.SALES)
        cls.other_user = create_user('meeting_update_other', role=CustomUser.Roles.SALES)
        cls.admin_user = create_user('meeting_update_admin', is_superuser=True)
        cls.account = Account.objects.create(name="Update Meeting Account", assigned_to=cls.owner_user)
        cls.meeting = Meeting.objects.create(
            subject="Update Test Meeting",
            status='PLANNED',
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
            location="Office",
            created_by=cls.owner_user,
            assigned_to=cls.owner_user,
            related_to_account=cls.account
        )
        cls.update_url = reverse('activities:meeting-update', kwargs={'pk': cls.meeting.pk})
        cls.list_url = reverse('activities:meeting-list')

    def test_get_page_as_owner(self):
        self.client.login(username='meeting_update_owner', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/meeting_form.html')
        self.assertEqual(response.context['form'].initial['subject'], self.meeting.subject)

    def test_permission_denied_for_other_user(self):
        self.client.login(username='meeting_update_other', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 404)

    def test_update_meeting_success_post(self):
        self.client.login(username='meeting_update_owner', password='password123')
        start_time_str = timezone.now().strftime('%Y-%m-%dT%H:%M')
        end_time_str = (timezone.now() + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')
        meeting_data = {
            'subject': 'Updated Test Meeting',
            'status': 'HELD',
            'start_time': start_time_str,
            'end_time': end_time_str,
            'location': 'Conference Room',
            'related_to_account': self.account.pk,
            'assigned_to': self.owner_user.pk
        }
        response = self.client.post(self.update_url, data=meeting_data)
        self.assertRedirects(response, self.list_url)
        self.meeting.refresh_from_db()
        self.assertEqual(self.meeting.subject, 'Updated Test Meeting')
        self.assertEqual(self.meeting.status, 'HELD')
        self.assertEqual(self.meeting.location, 'Conference Room')

    def test_update_meeting_invalid_input(self):
        self.client.login(username='meeting_update_owner', password='password123')
        initial_status = self.meeting.status
        start_time_str = timezone.now().strftime('%Y-%m-%dT%H:%M')
        end_time_str = (timezone.now() + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
        meeting_data = {
            'subject': '',
            'status': 'PLANNED',
            'start_time': start_time_str,
            'end_time': end_time_str,
            'location': 'Office',
            'related_to_account': self.account.pk,
            'assigned_to': self.owner_user.pk
        }
        response = self.client.post(self.update_url, data=meeting_data)
        self.assertEqual(response.status_code, 200)
        self.meeting.refresh_from_db()
        self.assertEqual(self.meeting.status, initial_status)
        self.assertFormError(response.context['form'], 'subject', 'This field is required.')
        self.assertTemplateUsed(response, 'activities/meeting_form.html')


class MeetingDeleteViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_user = create_user('meeting_delete_owner', role=CustomUser.Roles.SALES)
        cls.other_user = create_user('meeting_delete_other', role=CustomUser.Roles.SALES)
        cls.admin_user = create_user('meeting_delete_admin', is_superuser=True)
        cls.account = Account.objects.create(name="Delete Meeting Account", assigned_to=cls.owner_user)
        cls.meeting = Meeting.objects.create(
            subject="Delete Test Meeting",
            status='PLANNED',
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
            location="Office",
            created_by=cls.owner_user,
            assigned_to=cls.owner_user,
            related_to_account=cls.account
        )
        cls.delete_url = reverse('activities:meeting-delete', kwargs={'pk': cls.meeting.pk})
        cls.list_url = reverse('activities:meeting-list')

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.delete_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.delete_url}')

    def test_get_page_as_owner(self):
        self.client.login(username='meeting_delete_owner', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/meeting_confirm_delete.html')
        self.assertContains(response, self.meeting.subject)

    def test_delete_meeting_success_post(self):
        self.client.login(username='meeting_delete_owner', password='password123')
        initial_meeting_count = Meeting.objects.count()
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(Meeting.objects.count(), initial_meeting_count - 1)
        self.assertFalse(Meeting.objects.filter(pk=self.meeting.pk).exists())

    def test_permission_denied_for_other_user(self):
        self.client.login(username='meeting_delete_other', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 404)

    def test_delete_meeting_accessible_by_admin(self):
        self.client.login(username='meeting_delete_admin', password='password123')
        initial_meeting_count = Meeting.objects.count()
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(Meeting.objects.count(), initial_meeting_count - 1)
        self.assertFalse(Meeting.objects.filter(pk=self.meeting.pk).exists())