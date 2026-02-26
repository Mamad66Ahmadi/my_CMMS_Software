from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def index_view(request):
    return HttpResponse('<h1> Home page </h1>')

def contact_view(request):
    return HttpResponse('<h1> Contact page </h1>')