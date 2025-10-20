# sensores/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/sensores/$", consumers.SensorConsumer.as_asgi()),
]
