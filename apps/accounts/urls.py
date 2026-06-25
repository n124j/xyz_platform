from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.ClientListView.as_view(), name="client_list"),
    path("<int:pk>/", views.ClientDetailView.as_view(), name="client_detail"),
    path(
        "account/<str:account_number>/",
        views.AccountDetailView.as_view(),
        name="account_detail",
    ),
]
