from django.db import models
from django.contrib.auth.models import User


class Task(models.Model):
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    active      = models.BooleanField(default=True)
    project     = models.ForeignKey(
        'projects.Project',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='tasks',
    )
    owner       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Execution(models.Model):
    title       = models.CharField(max_length=200)
    task        = models.ForeignKey(
        Task,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='executions',
    )
    description = models.TextField(blank=True)
    owner       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='executions')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
