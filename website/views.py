from django.shortcuts import render, redirect
from .forms import ContactForm

def index_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']

            print(name, email)

            return redirect('home')
    else:
        form = ContactForm()

    return render(request, 'website/index.html', {'form': form})

def contact_view(request):
    return render(request,'website/contact.html')

