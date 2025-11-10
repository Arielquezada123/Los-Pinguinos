from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Alerta

@login_required
def reportes_pagina(request):
    
    alertas = Alerta.objects.filter(usuario=request.user.usuario)
    
    context = {
        'alertas_list': alertas
    }
    return render(request, 'dashboard_reportes.html', context)