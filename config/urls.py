"""XYZ Platform — Root URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Auth
    path("accounts/login/", auth_views.LoginView.as_view(template_name="base/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),

    # XYZ Apps
    path("", include("apps.portfolio.urls", namespace="portfolio")),
    path("dashboard/", include("apps.portfolio.urls", namespace="portfolio_dash")),
    path("clients/", include("apps.accounts.urls", namespace="accounts")),
    path("analytics/", include("apps.analytics.urls", namespace="analytics")),
    path("etl/", include("apps.etl_monitor.urls", namespace="etl_monitor")),

    # Plotly Dash
    path("django_plotly_dash/", include("django_plotly_dash.urls")),

    # DRF API
    path("api/v1/portfolio/", include("apps.portfolio.api_urls")),
    path("api/v1/accounts/", include("apps.accounts.api_urls")),
    path("api/v1/analytics/", include("apps.analytics.api_urls")),
    path("api/v1/etl/", include("apps.etl_monitor.api_urls")),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
