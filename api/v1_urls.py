from django.urls import path
from . import views

# Rutas sin namespace — montadas en /v1/ desde shirkaai/urls.py
urlpatterns = [
    path('models',             views.v1_list_models,      name='v1_models'),
    path('chat/completions',   views.v1_chat_completions, name='v1_chat_completions'),
]
