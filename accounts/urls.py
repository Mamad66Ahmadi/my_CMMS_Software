# accounts/urls.py

from django.urls import path, include
from django.contrib.auth import views as auth_views

from .views import UserDashboardView


app_name = "accounts"

urlpatterns = [

    path('api/v1/', include('accounts.api.v1.urls')),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True
        ),
        name="login",
    ),

    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="accounts:login"),
        name="logout",
    ),

    path("dashboard/", UserDashboardView.as_view(), name="dashboard"),


]