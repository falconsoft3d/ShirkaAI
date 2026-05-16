from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('',                      views.project_list,      name='list'),
    path('new/',                  views.project_new,       name='new'),
    path('create/',               views.project_create,    name='create'),
    path('<int:pk>/set-model/',   views.project_set_model, name='set_model'),
    path('<int:pk>/set-api/',     views.project_set_api,   name='set_api'),
    path('<int:pk>/delete/',       views.project_delete,      name='delete'),
    path('<int:pk>/clear-memory/',  views.project_clear_memory, name='clear_memory'),
    path('<int:pk>/memory/',         views.project_memory,        name='memory'),
]
