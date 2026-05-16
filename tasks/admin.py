from django.contrib import admin
from .models import Task

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display  = ('title', 'owner', 'project', 'active', 'created_at')
    list_filter   = ('active', 'project')
    search_fields = ('title', 'description')
