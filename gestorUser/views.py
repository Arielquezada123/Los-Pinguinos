from django.shortcuts import render , redirect
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from .models import Usuario
from .forms import SignUpForm
from .forms import LimiteMensualForm
from django.contrib import messages
from .models import Usuario


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
    except Usuario.DoesNotExist:
        rol = Usuario.objects.create(usuario=request.user).rol
    except Exception as e:
        print(f"Error al obtener el rol del usuario: {e}")
        return redirect('index') 
    if rol == Usuario.Rol.EMPRESA:
        
        return redirect('empresa_inicio')
    else:
        return render(request, 'dashboard_inicio.html')

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
    