from django.test import TestCase
from django.urls import reverse
from users.models import CustomUser

class DashboardViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.test_user = CustomUser.objects.create_user(
            username='testuser_dashboard', password='password123', email='dashboard@example.com'
        )

    def test_dashboard_view_authenticated(self):
        login_successful = self.client.login(username='testuser_dashboard', password='password123')
        self.assertTrue(login_successful)
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
        self.assertContains(response, "Welcome,")

    def test_dashboard_view_unauthenticated(self):
        response = self.client.get(reverse('core:dashboard'))
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next=/')
        
    def test_dashboard_displays_user_data(self):
        self.client.login(username='testuser_dashboard', password='password123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.test_user.username)
        self.assertContains(response, 'Sales Associate')

    def test_dashboard_displays_no_activities(self):
        from activities.models import Call
        self.client.login(username='testuser_dashboard', password='password123')
        Call.objects.create(
            subject='Test Call',
            status='COMPLETED',
            direction='OUTGOING',
            duration_minutes=30,
            assigned_to=self.test_user,
            created_by=self.test_user
        )
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No upcoming calls')
        
    def test_dashboard_quick_actions(self):
        self.client.login(username='testuser_dashboard', password='password123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'New Account')
        self.assertContains(response, 'New Contact')
        self.assertContains(response, 'New Lead')

    def test_dashboard_lead_summary(self):
        self.client.login(username='testuser_dashboard', password='password123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Lead Summary')
        self.assertContains(response, 'No open leads found')
        
    def test_dashboard_contains_user_data(self):
        self.client.login(username='testuser_dashboard', password='password123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.test_user.username)