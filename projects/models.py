from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    API_PROVIDER_CHOICES = [
        ('local',  'Modelo local (GGUF)'),
        ('openai', 'OpenAI – ChatGPT'),
    ]
    OPENAI_MODEL_CHOICES = [
        ('gpt-4o-mini',   'GPT-4o Mini  (recomendado)'),
        ('gpt-4o',        'GPT-4o'),
        ('gpt-4-turbo',   'GPT-4 Turbo'),
        ('gpt-3.5-turbo', 'GPT-3.5 Turbo'),
        ('o1-mini',       'o1 Mini'),
    ]

    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    model       = models.ForeignKey(
        'llm_models.LLMModel',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='projects',
        limit_choices_to={'status__in': ['ready', 'active']},
    )
    owner       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')

    # ── Configuración de API externa ──────────────────────────────────────
    api_provider   = models.CharField(
        max_length=20, choices=API_PROVIDER_CHOICES, default='local',
    )
    api_key        = models.CharField(max_length=300, blank=True)
    api_model_name = models.CharField(max_length=100, blank=True, default='gpt-4o-mini')

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_chat_ready(self):
        if self.api_provider == 'openai':
            return bool(self.api_key)
        return bool(self.model and self.model.status in ['ready', 'active'])

    @property
    def api_key_masked(self):
        k = self.api_key
        if not k:
            return ''
        if len(k) <= 12:
            return '••••'
        return k[:8] + '•' * (len(k) - 12) + k[-4:]
