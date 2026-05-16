from django.db import models
from projects.models import Project


def _upload_to(instance, filename):
    return f'docs/{instance.project_id}/{filename}'


class ProjectDocument(models.Model):
    TYPE_TEXT = 'text'
    TYPE_PDF  = 'pdf'
    TYPE_CHOICES = [
        ('text', 'Texto'),
        ('pdf',  'PDF'),
    ]

    project  = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='documents')
    title    = models.CharField(max_length=200)
    doc_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='text')
    content  = models.TextField(blank=True)
    file     = models.FileField(upload_to=_upload_to, blank=True, null=True)
    # ── Estado de indexación vectorial ──────────────────────────────────────
    INDEX_PENDING  = 'pending'
    INDEX_INDEXING = 'indexing'
    INDEX_PAUSED   = 'paused'
    INDEX_DONE     = 'done'
    INDEX_ERROR    = 'error'
    INDEX_STATUS_CHOICES = [
        ('pending',  'Pendiente'),
        ('indexing', 'Indexando'),
        ('paused',   'Pausado'),
        ('done',     'Indexado'),
        ('error',    'Error'),
    ]
    index_status  = models.CharField(
        max_length=10, choices=INDEX_STATUS_CHOICES, default='pending'
    )
    chunk_count   = models.IntegerField(default=0)
    index_progress = models.IntegerField(default=0)   # 0-100
    index_error   = models.CharField(max_length=500, blank=True)
    # ────────────────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.project.name})'

    @property
    def file_size_label(self):
        if not self.file:
            return ''
        try:
            size = self.file.size
            if size < 1024:
                return f'{size} B'
            elif size < 1024 * 1024:
                return f'{size / 1024:.1f} KB'
            return f'{size / (1024 * 1024):.1f} MB'
        except Exception:
            return ''
