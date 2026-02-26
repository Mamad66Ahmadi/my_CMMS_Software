from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def index_view(request):
    return render(request,'website/index.html')

def contact_view(request):
    return render(request,'website/contact.html')