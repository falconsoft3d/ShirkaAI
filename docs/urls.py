from django.urls import path
from . import views

app_name = 'docs'

urlpatterns = [
    path('<int:project_pk>/',        views.doc_list,         name='list'),
    path('<int:project_pk>/create/', views.doc_create,       name='create'),
    path('<int:pk>/delete/',         views.doc_delete,       name='delete'),
    path('<int:pk>/reindex/',        views.doc_reindex,      name='reindex'),
    path('<int:pk>/status/',         views.doc_index_status, name='status'),
    path('<int:pk>/pause/',          views.doc_pause,        name='pause'),
    path('<int:pk>/resume/',         views.doc_resume,       name='resume'),
]
