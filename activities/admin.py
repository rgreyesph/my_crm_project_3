# activities/admin.py
from django.contrib import admin
from .models import Task, Call, Meeting

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('subject', 'due_date', 'status', 'priority', 'assigned_to', 'related_object_link', 'updated_at')
    list_filter = ('status', 'priority', 'assigned_to', 'due_date')
    search_fields = ('subject', 'description')
    autocomplete_fields = ['related_to_account', 'related_to_contact', 'related_to_lead', 'related_to_deal', 'assigned_to']
    date_hierarchy = 'due_date'

    # Helper to display related object concisely
    def related_object_link(self, obj):
        if obj.related_to_account: return f"Acc: {obj.related_to_account}"
        if obj.related_to_contact: return f"Cont: {obj.related_to_contact}"
        if obj.related_to_lead: return f"Lead: {obj.related_to_lead}"
        if obj.related_to_deal: return f"Deal: {obj.related_to_deal}"
        return "--"
    related_object_link.short_description = 'Related To'


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ('subject', 'call_time', 'direction', 'status', 'assigned_to', 'related_object_link', 'updated_at')
    list_filter = ('direction', 'status', 'assigned_to', 'call_time')
    search_fields = ('subject', 'notes')
    autocomplete_fields = ['related_to_account', 'related_to_contact', 'related_to_lead', 'related_to_deal', 'assigned_to']
    date_hierarchy = 'call_time'

    # Helper (can be made more generic later)
    def related_object_link(self, obj):
        if obj.related_to_account: return f"Acc: {obj.related_to_account}"
        if obj.related_to_contact: return f"Cont: {obj.related_to_contact}"
        if obj.related_to_lead: return f"Lead: {obj.related_to_lead}"
        if obj.related_to_deal: return f"Deal: {obj.related_to_deal}"
        return "--"
    related_object_link.short_description = 'Related To'


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('subject', 'start_time', 'location', 'status', 'assigned_to', 'related_object_link', 'updated_at')
    list_filter = ('status', 'assigned_to', 'start_time', 'location')
    search_fields = ('subject', 'description', 'location')
    autocomplete_fields = ['related_to_account', 'related_to_contact', 'related_to_lead', 'related_to_deal', 'assigned_to']
    date_hierarchy = 'start_time'

    # Helper
    def related_object_link(self, obj):
        if obj.related_to_account: return f"Acc: {obj.related_to_account}"
        if obj.related_to_contact: return f"Cont: {obj.related_to_contact}"
        if obj.related_to_lead: return f"Lead: {obj.related_to_lead}"
        if obj.related_to_deal: return f"Deal: {obj.related_to_deal}"
        return "--"
    related_object_link.short_description = 'Related To'