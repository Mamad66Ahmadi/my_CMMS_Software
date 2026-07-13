# permits/urls.py
from django.urls import path
from permits.views.permit_list_views import PermitList

app_name = "permits"

urlpatterns = [
    path("list/", PermitList.as_view(), name="permit_list"),
]
