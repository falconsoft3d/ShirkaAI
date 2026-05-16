from django.db import models


class LLMModel(models.Model):
    STATUS_DOWNLOADING = 'downloading'
    STATUS_READY = 'ready'
    STATUS_ACTIVE = 'active'
    STATUS_ERROR = 'error'

    STATUS_CHOICES = [
        (STATUS_DOWNLOADING, 'Descargando'),
        (STATUS_READY, 'Listo'),
        (STATUS_ACTIVE, 'Activo'),
        (STATUS_ERROR, 'Error'),
    ]

    catalog_id   = models.CharField(max_length=100, unique=True)
    name         = models.CharField(max_length=200)
    repo_id      = models.CharField(max_length=300)
    filename     = models.CharField(max_length=300)
    description  = models.TextField(blank=True)
    size_label   = models.CharField(max_length=20, blank=True)
    tags         = models.CharField(max_length=300, blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DOWNLOADING)
    progress     = models.IntegerField(default=0)
    local_path   = models.CharField(max_length=500, blank=True)
    error_message = models.TextField(blank=True)
    public       = models.BooleanField(default=False, help_text='Visible en el home público para cualquier visitante')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    @property
    def tags_list(self):
        return [t.strip() for t in self.tags.split(',') if t.strip()]

