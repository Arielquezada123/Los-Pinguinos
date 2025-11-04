from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import LecturaSensor
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
        # 1. Obtenemos el usuario (ya está en request.user gracias a @login_required)
        # 2. Filtramos las lecturas que pertenecen a dispositivos...
        #    ...cuyo perfil de usuario...
        #    ...pertenece al usuario de la solicitud actual.
        lecturas = LecturaSensor.objects.filter(
            dispositivo__usuario__usuario=request.user
        ).order_by('-timestamp')[:50] # Traemos las últimas 50

        # 3. Preparamos los datos para convertirlos a JSON
        data = [
            {
                "sensor_nombre": lectura.dispositivo.nombre or lectura.dispositivo.id_dispositivo_mqtt,
                "valor": lectura.valor_flujo,
                "timestamp": lectura.timestamp.isoformat() # Usamos formato ISO
            }
            for lectura in lecturas
        ]
        
        # 4. Devolvemos la lista de datos como JSON
        return JsonResponse(data, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500, safe=False)