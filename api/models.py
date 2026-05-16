import secrets
from django.db import models
from django.contrib.auth.models import User


class APIToken(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_tokens')
    name       = models.CharField(max_length=100)
    key        = models.CharField(max_length=64, unique=True, editable=False)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = secrets.token_hex(32)   # 64 hex chars
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.user.username})'

    @property
    def key_preview(self):
        return f'sk-shirka-{self.key[:8]}…'
