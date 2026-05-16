from django.urls import path
from . import views

app_name = 'llm_models'

urlpatterns = [
    path('',                              views.catalog,               name='catalog'),
    path('download/<str:catalog_id>/',    views.download_start,        name='download_start'),
    path('progress/<int:model_id>/',      views.download_progress_api, name='progress'),
    path('activate/<int:model_id>/',      views.activate_model,        name='activate'),
    path('deactivate/<int:model_id>/',    views.deactivate_model,      name='deactivate'),
    path('delete/<int:model_id>/',        views.delete_model,          name='delete'),
    path('toggle-public/<int:model_id>/',  views.toggle_public,         name='toggle_public'),
]
