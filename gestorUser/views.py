from django.shortcuts import render , redirect
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from .models import Usuario
from .forms import SignUpForm
from .forms import LimiteMensualForm
from django.contrib import messages



def signUp(request):
    usuario=Usuario
    form=SignUpForm
    if request.method == 'POST':
        form=SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/')
    return render(request,'forms/signUp.html',{'form':form})



@login_required(login_url='login')  
def postlogin(request):
    user = request.user
    if user.is_staff:
        return render(request,'dashboard_inicio.html')
    else:
        return render (request, 'dashboard_inicio.html')


@login_required
def limite_pagina(request):
    # Usamos request.user.usuario para obtener tu modelo de perfil
    usuario_perfil = request.user.usuario 

    if request.method == 'POST':
        form = LimiteMensualForm(request.POST, instance=usuario_perfil)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Límite mensual actualizado correctamente!')
            return redirect('limite_pagina') # Redirige a la misma página
    else:
        # Muestra el formulario con el valor actual de la base de datos
        form = LimiteMensualForm(instance=usuario_perfil)

    context = {
        'form': form
    }
    return render(request, 'dashboard_limite.html', context)
    