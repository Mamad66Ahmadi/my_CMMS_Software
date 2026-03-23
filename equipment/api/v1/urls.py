# equipment/api/v1/urls.py
from rest_framework import routers
from django.urls import path, include
from . import views


router = routers.DefaultRouter()
router.register(r'tag', views.LocationTagModelViewSet, basename='locationtag')

urlpatterns = [
    path('', include(router.urls)),
]

