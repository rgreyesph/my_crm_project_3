from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError
from users.models import CustomUser
from crm_entities.models import Account, Contact
from sales_pipeline.models import Deal
from ..models import Call, Task, Meeting


# Helper function
def create_user(username, role=CustomUser.Roles.SALES, is_superuser=False):
    """ Creates a user with specified role """
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
        email=f"{username}@example.com"
    )


class CallModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user('call_user')
        cls.admin = create_user('call_admin', is_superuser=True)
        cls.account = Account.objects.create(name="Test Account", assigned_to=cls.user)
        cls.contact = Contact.objects.create(
            last_name="Test Contact",
            account=cls.account,
            assigned_to=cls.user
        )
        cls.deal = Deal.objects.create(
            name="Test Deal",
            account=cls.account,
            stage=Deal.StageChoices.PROPOSAL,
            amount=1000,
            close_date=timezone.now().date(),
            assigned_to=cls.user
        )
        cls.call = Call.objects.create(
            subject="Test Call",
            status='PLANNED',
            direction='OUTGOING',
            duration_minutes=90,
            created_by=cls.user,
            assigned_to=cls.user,
            related_to_account=cls.account,
            related_to_contact=cls.contact,
            related_to_deal=cls.deal
        )

    def test_call_creation(self):
        self.assertEqual(self.call.subject, "Test Call")
        self.assertEqual(self.call.status, 'PLANNED')
        self.assertEqual(self.call.direction, 'OUTGOING')
        self.assertEqual(self.call.duration_minutes, 90)
        self.assertEqual(self.call.created_by, self.user)
        self.assertEqual(self.call.assigned_to, self.user)
        self.assertEqual(self.call.related_to_account, self.account)
        self.assertEqual(self.call.related_to_contact, self.contact)
        self.assertEqual(self.call.related_to_deal, self.deal)
        self.assertIsNotNone(self.call.created_at)
        self.assertIsNotNone(self.call.updated_at)

    def test_get_direction_display(self):
        self.assertEqual(self.call.get_direction_display(), "Outgoing")
        self.call.direction = 'INCOMING'
        self.assertEqual(self.call.get_direction_display(), "Incoming")

    def test_optional_fields_nullable(self):
        call = Call.objects.create(
            subject="Minimal Call",
            status='PLANNED',
            direction='OUTGOING',
            created_by=self.user,
            assigned_to=self.user
        )
        self.assertIsNone(call.duration_minutes)
        self.assertIsNone(call.related_to_account)
        self.assertIsNone(call.related_to_contact)
        self.assertIsNone(call.related_to_deal)

    def test_invalid_duration(self):
        self.call.duration_minutes = -10
        with self.assertRaises(ValidationError):
            self.call.full_clean()

    def test_status_choices(self):
        expected_choices = [
            ('PLANNED', 'Planned'),
            ('HELD', 'Held'),
            ('NOT_HELD', 'Not Held / Cancelled')
        ]
        self.assertEqual(Call._meta.get_field('status').choices, expected_choices)
        call = Call.objects.create(
            subject="Held Call",
            status='HELD',
            direction='OUTGOING',
            created_by=self.user,
            assigned_to=self.user
        )
        self.assertEqual(call.status, 'HELD')

    def test_str_method(self):
        self.assertEqual(str(self.call), "Test Call (Outgoing)")


class TaskModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user('task_user')
        cls.account = Account.objects.create(name="Test Account", assigned_to=cls.user)
        cls.contact = Contact.objects.create(
            last_name="Test Contact",
            account=cls.account,
            assigned_to=cls.user
        )
        cls.deal = Deal.objects.create(
            name="Test Deal",
            account=cls.account,
            stage=Deal.StageChoices.PROPOSAL,
            amount=1000,
            close_date=timezone.now().date(),
            assigned_to=cls.user
        )
        cls.task = Task.objects.create(
            subject="Test Task",
            status='NOT_STARTED',
            priority='NORMAL',
            due_date=timezone.now(),
            created_by=cls.user,
            assigned_to=cls.user,
            related_to_account=cls.account,
            related_to_contact=cls.contact,
            related_to_deal=cls.deal
        )

    def test_task_creation(self):
        self.assertEqual(self.task.subject, "Test Task")
        self.assertEqual(self.task.status, 'NOT_STARTED')
        self.assertEqual(self.task.priority, 'NORMAL')
        self.assertEqual(self.task.created_by, self.user)
        self.assertEqual(self.task.assigned_to, self.user)
        self.assertEqual(self.task.related_to_account, self.account)
        self.assertEqual(self.task.related_to_contact, self.contact)
        self.assertEqual(self.task.related_to_deal, self.deal)
        self.assertIsNotNone(self.task.created_at)
        self.assertIsNotNone(self.task.updated_at)

    def test_status_completed(self):
        self.assertEqual(self.task.status, 'NOT_STARTED')
        self.task.status = 'COMPLETED'
        self.task.save()
        self.assertEqual(self.task.status, 'COMPLETED')

    def test_optional_fields_nullable(self):
        task = Task.objects.create(
            subject="Minimal Task",
            status='NOT_STARTED',
            due_date=timezone.now(),
            created_by=self.user,
            assigned_to=self.user
        )
        self.assertEqual(task.priority, 'NORMAL')  # Default value
        self.assertIsNone(task.related_to_account)
        self.assertIsNone(task.related_to_contact)
        self.assertIsNone(task.related_to_deal)

    def test_status_choices(self):
        expected_choices = [
            ('NOT_STARTED', 'Not Started'),
            ('IN_PROGRESS', 'In Progress'),
            ('COMPLETED', 'Completed'),
            ('DEFERRED', 'Deferred')
        ]
        self.assertEqual(Task._meta.get_field('status').choices, expected_choices)
        task = Task.objects.create(
            subject="Completed Task",
            status='COMPLETED',
            due_date=timezone.now(),
            created_by=self.user,
            assigned_to=self.user
        )
        self.assertEqual(task.status, 'COMPLETED')

    def test_priority_choices(self):
        expected_choices = [('LOW', 'Low'), ('NORMAL', 'Normal'), ('HIGH', 'High')]
        self.assertEqual(Task._meta.get_field('priority').choices, expected_choices)
        task = Task.objects.create(
            subject="High Priority Task",
            status='NOT_STARTED',
            priority='HIGH',
            due_date=timezone.now(),
            created_by=self.user,
            assigned_to=self.user
        )
        self.assertEqual(task.priority, 'HIGH')

    def test_str_method(self):
        self.assertEqual(str(self.task), "Test Task")


class MeetingModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user('meeting_user')
        cls.account = Account.objects.create(name="Test Account", assigned_to=cls.user)
        cls.contact = Contact.objects.create(
            last_name="Test Contact",
            account=cls.account,
            assigned_to=cls.user
        )
        cls.deal = Deal.objects.create(
            name="Test Deal",
            account=cls.account,
            stage=Deal.StageChoices.PROPOSAL,
            amount=1000,
            close_date=timezone.now().date(),
            assigned_to=cls.user
        )
        cls.start_time = timezone.now()
        cls.end_time = cls.start_time + timedelta(hours=1)
        cls.meeting = Meeting.objects.create(
            subject="Test Meeting",
            status='PLANNED',
            start_time=cls.start_time,
            end_time=cls.end_time,
            location="Test Location",
            created_by=cls.user,
            assigned_to=cls.user,
            related_to_account=cls.account,
            related_to_contact=cls.contact,
            related_to_deal=cls.deal
        )

    def test_meeting_creation(self):
        self.assertEqual(self.meeting.subject, "Test Meeting")
        self.assertEqual(self.meeting.status, 'PLANNED')
        self.assertEqual(self.meeting.start_time, self.start_time)
        self.assertEqual(self.meeting.end_time, self.end_time)
        self.assertEqual(self.meeting.location, "Test Location")
        self.assertEqual(self.meeting.created_by, self.user)
        self.assertEqual(self.meeting.assigned_to, self.user)
        self.assertEqual(self.meeting.related_to_account, self.account)
        self.assertEqual(self.meeting.related_to_contact, self.contact)
        self.assertEqual(self.meeting.related_to_deal, self.deal)
        self.assertIsNotNone(self.meeting.created_at)
        self.assertIsNotNone(self.meeting.updated_at)

    def test_duration_calculation(self):
        duration_hours = (self.meeting.end_time - self.meeting.start_time).total_seconds() / 3600
        self.assertEqual(duration_hours, 1.0)  # 1 hour
        self.meeting.end_time = self.meeting.start_time + timedelta(minutes=30)
        duration_hours = (self.meeting.end_time - self.meeting.start_time).total_seconds() / 3600
        self.assertEqual(duration_hours, 0.5)  # 30 minutes
        self.meeting.end_time = self.meeting.start_time
        duration_hours = (self.meeting.end_time - self.meeting.start_time).total_seconds() / 3600
        self.assertEqual(duration_hours, 0.0)

    def test_optional_fields_nullable(self):
        meeting = Meeting.objects.create(
            subject="Minimal Meeting",
            status='PLANNED',
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
            created_by=self.user,
            assigned_to=self.user
        )
        self.assertEqual(meeting.location, '')  # Default empty string
        self.assertIsNone(meeting.related_to_account)
        self.assertIsNone(meeting.related_to_contact)
        self.assertIsNone(meeting.related_to_deal)

    def test_end_time_no_validation(self):
        self.meeting.end_time = self.meeting.start_time - timedelta(hours=1)
        try:
            self.meeting.full_clean()
        except ValidationError as e:
            self.fail(f"Unexpected ValidationError: {e}")

    def test_status_choices(self):
        expected_choices = [
            ('PLANNED', 'Planned'),
            ('HELD', 'Held'),
            ('NOT_HELD', 'Not Held / Cancelled')
        ]
        self.assertEqual(Meeting._meta.get_field('status').choices, expected_choices)
        meeting = Meeting.objects.create(
            subject="Held Meeting",
            status='HELD',
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
            created_by=self.user,
            assigned_to=self.user
        )
        self.assertEqual(meeting.status, 'HELD')

    def test_str_method(self):
        self.assertEqual(str(self.meeting), "Test Meeting")