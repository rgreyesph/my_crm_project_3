from datetime import timedelta, date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Count, F, DecimalField
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils import timezone
from django.views.generic import TemplateView

from dateutil.relativedelta import relativedelta
import openpyxl

from activities.models import (
    Task,
    Call,
    Meeting,
    TaskStatusChoices,
    CallMeetingStatusChoices,
)
from crm_entities.models import Account, Contact, Lead
from sales_performance.models import SalesTarget
from sales_pipeline.models import Deal, Quote
from sales_territories.models import Territory
from users.models import CustomUser
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def health_check(request):
    return HttpResponse("OK", status=200)

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def get_sales_progress(self, user_to_check, start_date, end_date):
        achieved_deals = Deal.objects.filter(
            assigned_to=user_to_check,
            stage=Deal.StageChoices.CLOSED_WON,
            close_date__gte=start_date,
            close_date__lte=end_date,
        )
        achieved_sum_result = achieved_deals.aggregate(total=Sum('amount'))
        return achieved_sum_result['total'] or 0

    def get_user_target_info(self, user_to_check, target_date):
        target_info = {
            'target': None,
            'amount': 0,
            'achieved': 0,
            'percent': 0,
        }
        try:
            target = SalesTarget.objects.filter(
                user=user_to_check,
                start_date__lte=target_date,
                end_date__gte=target_date,
            ).order_by('-end_date', '-start_date').first()
            if target:
                target_info['target'] = target
                target_info['amount'] = target.target_amount
                target_info['achieved'] = self.get_sales_progress(
                    user_to_check,
                    target.start_date,
                    target.end_date,
                )
                if target_info['amount'] > 0:
                    target_info['percent'] = round(
                        (target_info['achieved'] / target_info['amount']) * 100
                    )
        except Exception as e:
            print(f"Error getting target info for {user_to_check.username}: {e}")
        return target_info

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.now().date()
        context['title'] = 'Dashboard'

        one_week_later = today + timedelta(days=7)
        context['my_upcoming_tasks'] = Task.objects.filter(
            assigned_to=user,
            status__in=[
                TaskStatusChoices.NOT_STARTED,
                TaskStatusChoices.IN_PROGRESS,
            ],
        ).filter(
            Q(due_date__isnull=True) | Q(due_date__lte=one_week_later)
        ).order_by(
            'due_date',
            'priority',
        )[:5]
        context['my_overdue_tasks_count'] = Task.objects.filter(
            assigned_to=user,
            status__in=[
                TaskStatusChoices.NOT_STARTED,
                TaskStatusChoices.IN_PROGRESS,
            ],
            due_date__lt=today,
        ).count()
        context['my_upcoming_calls'] = Call.objects.filter(
            assigned_to=user,
            status=CallMeetingStatusChoices.PLANNED,
            call_time__date__lte=one_week_later,
        ).order_by('call_time')[:5]
        context['my_upcoming_meetings'] = Meeting.objects.filter(
            assigned_to=user,
            status=CallMeetingStatusChoices.PLANNED,
            start_time__date__lte=one_week_later,
        ).order_by('start_time')[:5]

        user_target_info = self.get_user_target_info(user, today)
        context['current_target'] = user_target_info['target']
        context['target_amount'] = user_target_info['amount']
        context['achieved_amount'] = user_target_info['achieved']
        context['progress_percent'] = user_target_info['percent']

        open_deal_stages = [
            Deal.StageChoices.PROSPECTING,
            Deal.StageChoices.QUALIFICATION,
            Deal.StageChoices.PROPOSAL,
            Deal.StageChoices.NEGOTIATION,
        ]
        open_quote_statuses = [
            Quote.StatusChoices.DRAFT,
            Quote.StatusChoices.PRESENTED,
        ]
        my_open_deals_qs = Deal.objects.filter(
            assigned_to=user,
            stage__in=open_deal_stages,
        )
        deals_by_stage = my_open_deals_qs.values('stage').annotate(count=Count('id'))
        context['deals_by_stage'] = {Deal.StageChoices(stage['stage']).label: stage['count'] for stage in deals_by_stage}  # Dict for chart labels/data
        
        my_pipeline_summary = my_open_deals_qs.aggregate(
            raw_total=Coalesce(
                Sum('amount'),
                0,
                output_field=DecimalField(),
            ),
            weighted_total=Coalesce(
                Sum(F('amount') * F('probability') / 100.0),
                0,
                output_field=DecimalField(),
            ),
        )
        context['my_open_deals_raw_total'] = my_pipeline_summary['raw_total']
        context['my_open_deals_weighted_total'] = my_pipeline_summary['weighted_total']
        context['my_open_deals'] = my_open_deals_qs.order_by('-close_date')[:5]
        context['my_open_quotes'] = Quote.objects.filter(
            assigned_to=user,
            status__in=open_quote_statuses,
        ).select_related('account').order_by('-updated_at')[:5]

        my_leads = Lead.objects.filter(assigned_to=user)
        open_lead_statuses = [
            Lead.StatusChoices.NEW,
            Lead.StatusChoices.CONTACTED,
            Lead.StatusChoices.QUALIFIED,
        ]
        context['my_open_leads'] = my_leads.filter(
            status__in=open_lead_statuses
        ).order_by('-created_at')[:5]
        my_leads_by_status = my_leads.exclude(
            status__in=[
                Lead.StatusChoices.CONVERTED,
                Lead.StatusChoices.LOST,
            ]
        ).values('status').annotate(count=Count('id')).order_by('status')
        context['my_leads_by_status'] = {
            Lead.StatusChoices(item['status']).label: item['count']
            for item in my_leads_by_status
        }
        my_leads_by_source = my_leads.exclude(
            status__in=[
                Lead.StatusChoices.CONVERTED,
                Lead.StatusChoices.LOST,
            ]
        ).values('source').annotate(count=Count('id')).order_by('source')
        context['my_leads_by_source'] = {
            item['source']: item['count']
            for item in my_leads_by_source if item['source']
        }
        current_month_start = today.replace(day=1)
        prev_month_end = current_month_start - timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)
        context['leads_created_this_month'] = my_leads.filter(
            created_at__date__gte=current_month_start
        ).count()
        context['leads_created_last_month'] = my_leads.filter(
            created_at__date__range=(prev_month_start, prev_month_end)
        ).count()
        context['my_converted_leads_count'] = my_leads.filter(
            status=Lead.StatusChoices.CONVERTED
        ).count()

        context['tasks_completed_this_month'] = Task.objects.filter(
            assigned_to=user,
            status=TaskStatusChoices.COMPLETED,
            updated_at__date__gte=current_month_start,
        ).count()
        context['tasks_completed_last_month'] = Task.objects.filter(
            assigned_to=user,
            status=TaskStatusChoices.COMPLETED,
            updated_at__date__range=(prev_month_start, prev_month_end),
        ).count()
        context['calls_held_this_month'] = Call.objects.filter(
            assigned_to=user,
            status=CallMeetingStatusChoices.HELD,
            call_time__date__gte=current_month_start,
        ).count()
        context['calls_held_last_month'] = Call.objects.filter(
            assigned_to=user,
            status=CallMeetingStatusChoices.HELD,
            call_time__date__range=(prev_month_start, prev_month_end),
        ).count()
        context['meetings_held_this_month'] = Meeting.objects.filter(
            assigned_to=user,
            status=CallMeetingStatusChoices.HELD,
            start_time__date__gte=current_month_start,
        ).count()
        context['meetings_held_last_month'] = Meeting.objects.filter(
            assigned_to=user,
            status=CallMeetingStatusChoices.HELD,
            start_time__date__range=(prev_month_start, prev_month_end),
        ).count()

        context['my_recent_accounts'] = Account.objects.filter(
            Q(assigned_to=user) | Q(created_by=user)
        ).distinct().order_by('-updated_at')[:5]
        context['my_recent_contacts'] = Contact.objects.filter(
            Q(assigned_to=user) | Q(created_by=user)
        ).distinct().order_by('-updated_at')[:5]

        team_performance_data = []
        all_performance_data = []
        team_deals_by_stage_dict = {}
        all_deals_by_stage_dict = {}

        if user.is_manager_role or user.is_admin_role:
            if user.is_manager_role:
                try:
                    managed_territories = user.managed_territories.all()
                    team_members = CustomUser.objects.filter(
                        territory__in=managed_territories,
                        role=CustomUser.Roles.SALES,
                    ).exclude(pk=user.pk).order_by('first_name')
                    context['team_members'] = team_members
                    users_to_process = team_members
                except Exception as e:
                    print(f"Error getting team members for manager {user.username}: {e}")
                    users_to_process = CustomUser.objects.none()
            else:
                users_to_process = CustomUser.objects.filter(
                    role__in=[
                        CustomUser.Roles.SALES,
                        CustomUser.Roles.MANAGER,
                    ]
                ).order_by('first_name')
                context['admin_user_list_for_perf'] = users_to_process

            team_target_total = 0
            team_achieved_total = 0
            for member in users_to_process:
                member_target_info = self.get_user_target_info(member, today)
                if user.is_manager_role:
                    team_performance_data.append(
                        {'user': member, **member_target_info}
                    )
                if user.is_admin_role:
                    all_performance_data.append(
                        {'user': member, **member_target_info}
                    )
                if user.is_manager_role:
                    team_target_total += member_target_info['amount']
                    team_achieved_total += member_target_info['achieved']

            if user.is_manager_role:
                team_progress_percent = 0
                if team_target_total > 0:
                    team_progress_percent = round(
                        (team_achieved_total / team_target_total) * 100
                    )
                context['team_performance_data'] = team_performance_data
                context['team_target_total'] = team_target_total
                context['team_achieved_total'] = team_achieved_total
                context['team_progress_percent'] = team_progress_percent
                team_deals_stage_agg = Deal.objects.filter(
                    assigned_to__in=team_members,
                    stage__in=open_deal_stages,
                ).values('stage').annotate(
                    count=Count('id'),
                    weighted_value=Coalesce(
                        Sum(F('amount') * F('probability') / 100.0),
                        0,
                        output_field=DecimalField(),
                    ),
                ).order_by('stage')
                team_deals_by_stage_dict = {
                    Deal.StageChoices(item['stage']).label: {
                        'count': item['count'],
                        'weighted': item['weighted_value'],
                    }
                    for item in team_deals_stage_agg
                }
                context['team_deals_by_stage_weighted'] = team_deals_by_stage_dict
                context['team_open_quotes_count'] = Quote.objects.filter(
                    assigned_to__in=team_members,
                    status__in=open_quote_statuses,
                ).count()

            if user.is_admin_role:
                context['all_performance_data'] = all_performance_data
                all_deals_stage_agg = Deal.objects.filter(
                    stage__in=open_deal_stages
                ).values('stage').annotate(
                    count=Count('id'),
                    weighted_value=Coalesce(
                        Sum(F('amount') * F('probability') / 100.0),
                        0,
                        output_field=DecimalField(),
                    ),
                ).order_by('stage')
                context['all_deals_by_stage_weighted'] = {
                    Deal.StageChoices(item['stage']).label: {
                        'count': item['count'],
                        'weighted': item['weighted_value'],
                    }
                    for item in all_deals_stage_agg
                }
                context['all_open_quotes_count'] = Quote.objects.filter(
                    status__in=open_quote_statuses
                ).count()
                global_target_total = sum(
                    u['amount'] for u in all_performance_data
                )
                global_achieved_total = sum(
                    u['achieved'] for u in all_performance_data
                )
                global_progress_percent = 0
                if global_target_total > 0:
                    global_progress_percent = round(
                        (global_achieved_total / global_target_total) * 100
                    )
                context['global_target_total'] = global_target_total
                context['global_achieved_total'] = global_achieved_total
                context['global_progress_percent'] = global_progress_percent

        return context