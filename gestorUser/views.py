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
    return render(request,'forms/signUp.html',{'form':form})



@login_required
def postlogin(request):
    """
    Actúa como un enrutador después del login.
    Dirige al usuario a su panel correspondiente según su rol.
    """
    try:
        rol = request.user.usuario.rol
    except:
        return redirect('index') 

    if rol == 'EMPRESA':
        return redirect('empresa_inicio')
    else:
        return render(request, 'dashboard_inicio.html')

    