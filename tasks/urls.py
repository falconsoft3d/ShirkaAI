from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('',               views.task_list,   name='list'),
    path('new/',           views.task_new,    name='new'),
    path('<int:pk>/edit/', views.task_edit,   name='edit'),
    path('<int:pk>/toggle/', views.task_toggle, name='toggle'),
    path('<int:pk>/delete/', views.task_delete, name='delete'),

    # Executions
    path('executions/',               views.execution_list,   name='execution_list'),
    path('executions/new/',           views.execution_new,    name='execution_new'),
    path('executions/<int:pk>/edit/', views.execution_edit,   name='execution_edit'),
    path('executions/<int:pk>/delete/', views.execution_delete, name='execution_delete'),
]
