from django.contrib import admin
from .models import LLMModel


@admin.register(LLMModel)
class LLMModelAdmin(admin.ModelAdmin):
    list_display  = ('name', 'status', 'public', 'size_label', 'catalog_id')
    list_editable = ('public',)
    list_filter   = ('status', 'public')
    search_fields = ('name', 'catalog_id')
    readonly_fields = ('progress', 'error_message', 'local_path')
    fields = (
        'catalog_id', 'name', 'repo_id', 'filename', 'description',
        'size_label', 'tags', 'status', 'progress', 'local_path',
        'error_message', 'public',
    )
