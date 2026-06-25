"""XYZ Platform ASGI — supports Django Channels WebSocket connections."""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django_plotly_dash.consumers import MainConsumer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

django_asgi_app = get_asgi_application()

from django.urls import re_path  # noqa: E402 — must come after get_asgi_application

websocket_urlpatterns = [
    re_path(r"^ws/channel", MainConsumer.as_asgi()),
]

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
