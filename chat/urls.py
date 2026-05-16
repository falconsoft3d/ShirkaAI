from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('',                                             views.chat_home,           name='home'),
    path('<int:project_pk>/',                            views.chat_session,        name='project'),
    path('<int:project_pk>/session/<int:session_pk>/',   views.chat_session,        name='session'),
    path('<int:project_pk>/new/',                        views.chat_new_session,    name='new_session'),
    path('send/<int:session_pk>/',                       views.chat_send,           name='send'),
    path('delete/<int:session_pk>/',                     views.chat_delete_session, name='delete_session'),
]
