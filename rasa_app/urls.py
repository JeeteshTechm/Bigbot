# myproject/urls.py

from django.urls import path
from rasaapp.views import create_bot_view, chat_view

urlpatterns = [
    path('create_bot/', create_bot_view, name='create_bot'),
    path('chat/', chat_view, name='chat'),
]