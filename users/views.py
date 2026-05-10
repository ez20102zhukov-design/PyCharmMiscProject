from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect


def reg(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("/")
        else:
            print(form.errors)
    else:
        form = UserCreationForm()
    return render(request, 'reg.html', {'form': form})
# Create your views here.