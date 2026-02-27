from django.urls import path
from website.views import *

app_name = 'website'

urlpatterns = [
    path('',index_view, name='home'),
    path('contact/', contact_view, name='contact'),
]
