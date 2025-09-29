from django.shortcuts import render , redirect
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from .models import Usuario
from .forms import SignUpForm



def signUp(request):
    usuario=Usuario
    form=SignUpForm
    if request.method == 'POST':
        form=SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/')
    return render(request,'login.html',{'form':form})


@login_required(login_url='login')  
def postlogin(request):
    user = request.user
    if user.is_staff:
        return render(request,'base/login.html')
    else:
        return render (request, 'base/login.html')


    