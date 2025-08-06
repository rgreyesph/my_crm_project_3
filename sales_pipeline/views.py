from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)
from django.db.models import Q
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from django.utils.timezone import localtime
from dal import autocomplete
import openpyxl

# Import models needed
from .models import Deal, Quote
from .forms import DealForm, QuoteForm
from .filters import DealFilter, QuoteFilter
from users.models import CustomUser
from crm_entities.models import Account, Contact


# Base View Mixin
class BaseSalesPipelineView(LoginRequiredMixin):
    """Basic Mixin to require login and provide role-based filtering"""

    def _filter_queryset_by_role(self, user, queryset):
        if not hasattr(self, 'model'):
            return queryset.none()

        if user.is_admin_role:
            return queryset
        elif user.is_manager_role:
            try:
                managed_territories = user.managed_territories.all()
                team_members = CustomUser.objects.filter(
                    territory__in=managed_territories,
                    role=CustomUser.Roles.SALES
                ).exclude(pk=user.pk)

                base_q = (
                    Q(assigned_to=user) | Q(created_by=user) |
                    Q(assigned_to__in=team_members) |
                    Q(created_by__in=team_members)
                )
                if hasattr(self.model, 'account') and hasattr(Account, 'territory'):
                    base_q |= Q(account__territory__in=managed_territories)

                return queryset.filter(base_q).distinct()
            except Exception as e:
                print(f"Error applying manager role filter for {self.model.__name__}: {e}")
                return queryset.filter(
                    Q(assigned_to=user) | Q(created_by=user)
                ).distinct()
        elif user.is_sales_role:
            return queryset.filter(
                Q(assigned_to=user) | Q(created_by=user)
            ).distinct()
        else:
            return queryset.none()


# Deal Views
class DealListView(BaseSalesPipelineView, ListView):
    model = Deal
    context_object_name = 'deals'
    template_name = 'sales_pipeline/deal_list.html'
    paginate_by = 15
    sort_by_applied = 'deal_id'
    direction_applied = 'desc'

    def get_queryset(self):
        base_queryset = Deal.objects.all()
        queryset = self._filter_queryset_by_role(self.request.user, base_queryset)

        filter_params = self.request.GET.copy()
        filter_params.pop('sort', None)
        filter_params.pop('dir', None)
        filter_params.pop('page', None)
        self.filterset = DealFilter(filter_params, queryset=queryset)
        queryset = self.filterset.qs

        default_sort = '-deal_id'
        sort_by_param = self.request.GET.get('sort', default_sort)
        direction_param = self.request.GET.get(
            'dir',
            'desc' if default_sort.startswith('-') else 'asc'
        )
        valid_sort_fields = [
            'deal_id', 'name', 'account__name', 'stage', 'amount',
            'close_date', 'probability', 'assigned_to__username', 'updated_at'
        ]

        sort_by_validated = sort_by_param.lstrip('-')
        if sort_by_validated not in valid_sort_fields:
            sort_by_validated = default_sort.lstrip('-')
            direction_validated = 'desc' if default_sort.startswith('-') else 'asc'
        else:
            direction_validated = 'desc' if direction_param == 'desc' else 'asc'

        self.sort_by_applied = sort_by_validated
        self.direction_applied = direction_validated

        sort_by_final = (
            f'-{self.sort_by_applied}' if self.direction_applied == 'desc'
            else self.sort_by_applied
        )
        queryset = queryset.order_by(sort_by_final).select_related(
            'account', 'assigned_to', 'primary_contact'
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filterset'] = self.filterset
        context['sort_by'] = self.sort_by_applied
        context['direction'] = self.direction_applied
        context['opposite_direction'] = (
            'desc' if self.direction_applied == 'asc' else 'asc'
        )
        query_params = self.request.GET.copy()
        query_params.pop('sort', None)
        query_params.pop('dir', None)
        query_params.pop('page', None)
        context['current_filters_encoded'] = query_params.urlencode()
        return context


class DealDetailView(BaseSalesPipelineView, DetailView):
    model = Deal
    context_object_name = 'deal'
    template_name = 'sales_pipeline/deal_detail.html'

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related(
            'account', 'primary_contact', 'assigned_to', 'created_by'
        )
        return self._filter_queryset_by_role(user, queryset)


class DealCreateView(BaseSalesPipelineView, CreateView):
    model = Deal
    form_class = DealForm
    template_name = 'sales_pipeline/deal_form.html'
    success_url = reverse_lazy('sales_pipeline:deal-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Create New Deal / Opportunity'
        return context

    def get_initial(self):
        initial = super().get_initial()
        account_pk = self.request.GET.get('account')
        if account_pk:
            try:
                initial['account'] = Account.objects.get(pk=account_pk)
            except Account.DoesNotExist:
                messages.error(self.request, "Invalid Account specified.")
        contact_pk = self.request.GET.get('contact')
        if contact_pk:
            try:
                initial['primary_contact'] = Contact.objects.get(pk=contact_pk)
            except Contact.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        if hasattr(form.instance, 'assigned_to') and not form.instance.assigned_to:
            form.instance.assigned_to = self.request.user
        return super().form_valid(form)


class DealUpdateView(BaseSalesPipelineView, UpdateView):
    model = Deal
    form_class = DealForm
    template_name = 'sales_pipeline/deal_form.html'
    success_url = reverse_lazy('sales_pipeline:deal-list')

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        return self._filter_queryset_by_role(user, queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = (
            f'Update Deal: {self.object.deal_id or self.object.name}'
        )
        return context


class DealDeleteView(BaseSalesPipelineView, DeleteView):
    model = Deal
    template_name = 'sales_pipeline/deal_confirm_delete.html'
    success_url = reverse_lazy('sales_pipeline:deal-list')
    context_object_name = 'deal'

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        return self._filter_queryset_by_role(user, queryset)


# Quote Views
class QuoteListView(BaseSalesPipelineView, ListView):
    model = Quote
    context_object_name = 'quotes'
    template_name = 'sales_pipeline/quote_list.html'
    paginate_by = 15
    sort_by_applied = 'quote_id'
    direction_applied = 'desc'

    def get_queryset(self):
        base_queryset = Quote.objects.all()
        queryset = self._filter_queryset_by_role(self.request.user, base_queryset)

        filter_params = self.request.GET.copy()
        filter_params.pop('sort', None)
        filter_params.pop('dir', None)
        filter_params.pop('page', None)
        self.filterset = QuoteFilter(filter_params, queryset=queryset)
        queryset = self.filterset.qs

        default_sort = '-quote_id'
        sort_by_param = self.request.GET.get('sort', default_sort)
        direction_param = self.request.GET.get('dir', 'desc')
        valid_sort_fields = [
            'quote_id', 'account__name', 'deal__name', 'status',
            'total_amount', 'presented_date', 'assigned_to__username',
            'updated_at'
        ]

        sort_by_validated = sort_by_param.lstrip('-')
        if sort_by_validated not in valid_sort_fields:
            sort_by_validated = default_sort.lstrip('-')
            direction_validated = 'desc' if default_sort.startswith('-') else 'asc'
        else:
            direction_validated = 'desc' if direction_param == 'desc' else 'asc'

        self.sort_by_applied = sort_by_validated
        self.direction_applied = direction_validated

        sort_by_final = (
            f'-{self.sort_by_applied}' if self.direction_applied == 'desc'
            else self.sort_by_applied
        )
        queryset = queryset.order_by(sort_by_final).select_related(
            'account', 'deal', 'assigned_to', 'contact'
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filterset'] = self.filterset
        context['sort_by'] = self.sort_by_applied
        context['direction'] = self.direction_applied
        context['opposite_direction'] = (
            'desc' if self.direction_applied == 'asc' else 'asc'
        )
        query_params = self.request.GET.copy()
        query_params.pop('sort', None)
        query_params.pop('dir', None)
        query_params.pop('page', None)
        context['current_filters_encoded'] = query_params.urlencode()
        return context


class QuoteDetailView(BaseSalesPipelineView, DetailView):
    model = Quote
    context_object_name = 'quote'
    template_name = 'sales_pipeline/quote_detail.html'

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related(
            'account', 'deal', 'contact', 'assigned_to', 'created_by'
        )
        return self._filter_queryset_by_role(user, queryset)


class QuoteCreateView(BaseSalesPipelineView, CreateView):
    model = Quote
    form_class = QuoteForm
    template_name = 'sales_pipeline/quote_form.html'
    success_url = reverse_lazy('sales_pipeline:quote-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Create New Quote'
        return context

    def get_initial(self):
        initial = super().get_initial()
        if self.request.user.is_authenticated:
            initial['assigned_to'] = self.request.user
        deal_pk = self.request.GET.get('deal')
        if deal_pk:
            try:
                deal_obj = Deal.objects.select_related(
                    'account', 'primary_contact'
                ).get(pk=deal_pk)
                initial['deal'] = deal_obj
                if deal_obj.primary_contact:
                    initial['contact'] = deal_obj.primary_contact
            except Deal.DoesNotExist:
                messages.error(self.request, "Invalid Deal specified.")
        return initial

    def form_valid(self, form):
        deal = form.cleaned_data.get('deal')
        if deal and deal.account:
            form.instance.account = deal.account
        else:
            messages.error(
                self.request,
                "Selected Deal must have an associated Account."
            )
            return self.form_invalid(form)
        form.instance.created_by = self.request.user
        if hasattr(form.instance, 'assigned_to') and not form.cleaned_data.get('assigned_to'):
            form.instance.assigned_to = self.request.user
        return super().form_valid(form)


class QuoteUpdateView(BaseSalesPipelineView, UpdateView):
    model = Quote
    form_class = QuoteForm
    template_name = 'sales_pipeline/quote_form.html'
    success_url = reverse_lazy('sales_pipeline:quote-list')

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        return self._filter_queryset_by_role(user, queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        display_id = (
            self.object.quote_id if self.object.quote_id
            else f"#{self.object.pk}"
        )
        context['form_title'] = f'Update Quote: {display_id}'
        return context

    def form_valid(self, form):
        deal = form.cleaned_data.get('deal')
        if deal and deal.account:
            form.instance.account = deal.account
        else:
            messages.error(self.request, "A valid Deal must be selected.")
            return self.form_invalid(form)
        return super().form_valid(form)


class QuoteDeleteView(BaseSalesPipelineView, DeleteView):
    model = Quote
    template_name = 'sales_pipeline/quote_confirm_delete.html'
    success_url = reverse_lazy('sales_pipeline:quote-list')
    context_object_name = 'quote'

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        return self._filter_queryset_by_role(user, queryset)


# Autocomplete Views
class DealAutocomplete(LoginRequiredMixin, autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Deal.objects.all()
        if self.request.user.is_admin_role:
            pass
        elif self.request.user.is_manager_role:
            try:
                managed_territories = self.request.user.managed_territories.all()
                team_members = CustomUser.objects.filter(
                    territory__in=managed_territories,
                    role=CustomUser.Roles.SALES
                ).exclude(pk=self.request.user.pk)
                qs = qs.filter(
                    Q(assigned_to=self.request.user) |
                    Q(created_by=self.request.user) |
                    Q(assigned_to__in=team_members) |
                    Q(created_by__in=team_members) |
                    Q(account__territory__in=managed_territories)
                ).distinct()
            except Exception:
                qs = qs.filter(
                    Q(assigned_to=self.request.user) |
                    Q(created_by=self.request.user)
                ).distinct()
        elif self.request.user.is_sales_role:
            qs = qs.filter(
                Q(assigned_to=self.request.user) |
                Q(created_by=self.request.user)
            ).distinct()
        else:
            qs = Deal.objects.none()

        if self.q:
            qs = qs.filter(
                Q(name__icontains=self.q) |
                Q(deal_id__icontains=self.q) |
                Q(account__name__icontains=self.q)
            ).distinct()
        return qs.order_by('name')

    def get_result_label(self, item):
        return str(item)


# Export Views
@login_required
def deal_export_view(request):
    if not request.user.is_admin_role:
        return HttpResponseForbidden("Permission Denied.")
    base_queryset = Deal.objects.all()
    filterset = DealFilter(request.GET, queryset=base_queryset)
    queryset = filterset.qs
    sort_by_param = request.GET.get('sort', '-close_date')
    direction_param = request.GET.get('dir', 'desc')
    valid_sort_fields = [
        'deal_id', 'name', 'account__name', 'stage', 'amount',
        'close_date', 'probability', 'assigned_to__username',
        'updated_at'
    ]
    sort_by_validated = sort_by_param.lstrip('-')
    if sort_by_validated not in valid_sort_fields:
        sort_by_validated = 'close_date'
        direction_validated = 'desc'
    else:
        direction_validated = 'desc' if direction_param == 'desc' else 'asc'
    sort_by_final = (
        f'-{sort_by_validated}' if direction_validated == 'desc'
        else sort_by_validated
    )
    queryset = queryset.order_by(sort_by_final).select_related(
        'account', 'primary_contact', 'assigned_to', 'created_by'
    )
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Deals"
    headers = [
        "Deal ID", "Name", "Account", "Primary Contact", "Stage",
        "Amount", "Currency", "Close Date", "Probability (%)",
        "Description", "Assigned To", "Created By", "Created At",
        "Updated At"
    ]
    ws.append(headers)
    for deal in queryset:
        account_name = deal.account.name if deal.account else ""
        contact_name = (
            deal.primary_contact.full_name if deal.primary_contact else ""
        )
        assigned_to_name = (
            deal.assigned_to.get_full_name() or deal.assigned_to.username
            if deal.assigned_to else ""
        )
        created_by_name = (
            deal.created_by.get_full_name() or deal.created_by.username
            if deal.created_by else ""
        )
        created_at_formatted = (
            localtime(deal.created_at).strftime('%Y-%m-%d %H:%M:%S')
            if deal.created_at else ""
        )
        updated_at_formatted = (
            localtime(deal.updated_at).strftime('%Y-%m-%d %H:%M:%S')
            if deal.updated_at else ""
        )
        row = [
            deal.deal_id or "", deal.name or "", account_name,
            contact_name, deal.get_stage_display(), deal.amount,
            deal.currency or "", deal.close_date, deal.probability,
            deal.description or "", assigned_to_name, created_by_name,
            created_at_formatted, updated_at_formatted
        ]
        ws.append(row)
    response = HttpResponse(
        content_type=(
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet'
        )
    )
    response['Content-Disposition'] = 'attachment; filename="deals_export.xlsx"'
    wb.save(response)
    return response


@login_required
def quote_export_view(request):
    if not request.user.is_admin_role:
        return HttpResponseForbidden("Permission Denied.")
    base_queryset = Quote.objects.all()
    filterset = QuoteFilter(request.GET, queryset=base_queryset)
    queryset = filterset.qs
    sort_by_param = request.GET.get('sort', 'quote_id')
    direction_param = request.GET.get('dir', 'asc')
    valid_sort_fields = [
        'quote_id', 'account__name', 'deal__name', 'status',
        'total_amount', 'presented_date', 'assigned_to__username',
        'updated_at'
    ]
    sort_by_validated = sort_by_param.lstrip('-')
    if sort_by_validated not in valid_sort_fields:
        sort_by_validated = 'quote_id'
        direction_validated = 'asc'
    else:
        direction_validated = 'desc' if direction_param == 'desc' else 'asc'
    sort_by_final = (
        f'-{sort_by_validated}' if direction_validated == 'desc'
        else sort_by_validated
    )
    queryset = queryset.order_by(sort_by_final).select_related(
        'account', 'deal', 'contact', 'assigned_to', 'created_by'
    )
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Quotes"
    headers = [
        "Quote ID", "Account", "Deal ID", "Contact", "Status",
        "Total Amount", "Presented Date", "Validity (Days)",
        "Expiry Date", "Notes", "Assigned To", "Created By",
        "Created At", "Updated At"
    ]
    ws.append(headers)
    for quote in queryset:
        account_name = quote.account.name if quote.account else ""
        deal_id_str = (
            quote.deal.deal_id if quote.deal and quote.deal.deal_id
            else (quote.deal.pk if quote.deal else "")
        )
        contact_name = quote.contact.full_name if quote.contact else ""
        assigned_to_name = (
            quote.assigned_to.get_full_name() or quote.assigned_to.username
            if quote.assigned_to else ""
        )
        created_by_name = (
            quote.created_by.get_full_name() or quote.created_by.username
            if quote.created_by else ""
        )
        created_at_formatted = (
            localtime(quote.created_at).strftime('%Y-%m-%d %H:%M:%S')
            if quote.created_at else ""
        )
        updated_at_formatted = (
            localtime(quote.updated_at).strftime('%Y-%m-%d %H:%M:%S')
            if quote.updated_at else ""
        )
        expiry_date_val = quote.expiry_date
        row = [
            quote.quote_id or "", account_name, deal_id_str,
            contact_name, quote.get_status_display(),
            quote.total_amount, quote.presented_date,
            quote.validity_days, expiry_date_val, quote.notes or "",
            assigned_to_name, created_by_name, created_at_formatted,
            updated_at_formatted
        ]
        ws.append(row)
    response = HttpResponse(
        content_type=(
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet'
        )
    )
    response['Content-Disposition'] = 'attachment; filename="quotes_export.xlsx"'
    wb.save(response)
    return response