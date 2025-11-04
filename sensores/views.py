from django.shortcuts import render, redirect 
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import LecturaSensor, Dispositivo 
from .forms import DispositivoForm 
import json

# @login_required
# def tu_vista_dashboard(request):
#     return render(request, 'DemoDashboard.html')

@login_required
def historial_consumo(request):
    """
    Una vista de API que devuelve las últimas 50 lecturas 
    históricas para el usuario autenticado.
    """
    try:

        lecturas = LecturaSensor.objects.filter(
            dispositivo__usuario__usuario=request.user
        ).order_by('-timestamp')[:50] 

        #Preparamos los datos para convertirlos a JSON
        data = [
            {
                "sensor_nombre": lectura.dispositivo.nombre or lectura.dispositivo.id_dispositivo_mqtt,
                "valor": lectura.valor_flujo,
                "timestamp": lectura.timestamp.isoformat() #Usamos formato ISO
            }
            for lectura in lecturas
        ]
        
        #Devolvemos la lista de datos como JSON
        return JsonResponse(data, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500, safe=False)

@login_required
def historial_pagina_view(request):
    return render(request, 'dashboard_historial.html')

@login_required
def consumo_pagina_view(request):
    return render(request, 'dashboard_consumo.html')

@login_required
def mapa_pagina_view(request):
    return render(request, 'dashboard_mapa.html')

@login_required
def ingreso_pagina_view(request):

    if request.method == 'POST':
        form = DispositivoForm(request.POST)
        if form.is_valid():
            # Guardamos el formulario pero sin enviarlo a la DB todavía (commit=False)
            dispositivo = form.save(commit=False)
            # Asignamos el perfil de usuario (Usuario) que está logueado
            # request.user es el 'User' de Django, request.user.usuario es el 'Usuario' de gestorUser
            dispositivo.usuario = request.user.usuario
            
            # Ahora sí, guardamos en la base de datos
            dispositivo.save()
            # Redirigimos al usuario al inicio del dashboard
            return redirect('post_login') 
    
    # Si el método es GET (o si el formulario no fue válido), mostramos la página
    else:
        form = DispositivoForm()

    # Renderizamos la plantilla y le pasamos el formulario
    return render(request, 'dashboard_ingreso.html', {
        'form': form
    })