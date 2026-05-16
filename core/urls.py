from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('settings/profile/', views.profile_view, name='profile'),
    path('settings/users/', views.settings_users, name='settings_users'),
    path('settings/users/new/', views.user_new, name='user_new'),
    path('settings/users/create/', views.user_create, name='user_create'),
    path('settings/users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('settings/users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    # Chat público
    path('chat-publico/<int:pk>/', views.public_chat, name='public_chat'),
    path('chat-publico/<int:pk>/send/', views.public_chat_send, name='public_chat_send'),
    path('chat-publico/<int:pk>/clear/', views.public_chat_clear, name='public_chat_clear'),
]
