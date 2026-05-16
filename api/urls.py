from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('docs/',               views.api_docs,     name='docs'),
    path('tokens/',             views.api_tokens,   name='tokens'),
    path('tokens/create/',      views.create_token, name='create_token'),
    path('tokens/<int:pk>/revoke/', views.revoke_token, name='revoke_token'),
]
