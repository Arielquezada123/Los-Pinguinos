from django.shortcuts import render, redirect 
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import LecturaSensor, Dispositivo 
from .forms import DispositivoForm 
import json
from django.db.models import Sum
from django.db.models.functions import TruncMonth, TruncWeek
from datetime import datetime
from .models import Dispositivo
from django.utils.html import mark_safe
from django.db.models import OuterRef, Subquery, FloatField
from django.shortcuts import render, redirect, get_object_or_404

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

@login_required
def mapa_pagina_view(request):
    """
    Renderiza la página del mapa, pasando las ubicaciones y la ÚLTIMA LECTURA
    para evitar el estado de "espera" en los pop-ups.
    """
    
    # 1. Definir la subconsulta para obtener el valor de la última lectura (el más reciente)
    ultima_lectura_qs = LecturaSensor.objects.filter(
        dispositivo=OuterRef('pk') # Filtra por el ID del dispositivo principal
    ).order_by('-timestamp')

    # 2. Anotar los dispositivos con la última lectura (usando Subquery)
    dispositivos_con_ultima_lectura = Dispositivo.objects.filter(
        usuario__usuario=request.user,
        latitud__isnull=False, 
        longitud__isnull=False
    ).annotate(
        # Obtenemos el valor_flujo de la LecturaSensor más reciente
        last_flow_value=Subquery(
            ultima_lectura_qs.values('valor_flujo')[:1],
            output_field=FloatField()
        )
    ).values('nombre', 'id_dispositivo_mqtt', 'latitud', 'longitud', 'last_flow_value') # Incluimos el nuevo campo

    # 3. Serializar los datos, incluyendo el último valor
    locations_list = [
        {
            'nombre': d['nombre'] or d['id_dispositivo_mqtt'],
            'id_mqtt': d['id_dispositivo_mqtt'], 
            'lat': d['latitud'],
            'lon': d['longitud'],
            'last_value': d['last_flow_value'] if d['last_flow_value'] is not None else 0.0,
        }
        for d in dispositivos_con_ultima_lectura
    ]
    
    locations_json = mark_safe(json.dumps(locations_list))

    return render(request, 'dashboard_mapa.html', {
        'locations_json': locations_json
    })

@login_required
def api_historial_agregado(request):
    """
    API que devuelve datos de consumo agregados, separados por sensor,
    para los gráficos del historial. Acepta ?agrupar_por=mes|semana
    """
    try:
        agrupar_por = request.GET.get('agrupar_por', 'mes')
        lecturas = LecturaSensor.objects.filter(
            dispositivo__usuario__usuario=request.user
        )

        if agrupar_por == 'semana':
            TruncClase = TruncWeek('timestamp')
            formato_fecha = "Semana %W, %Y"
        else:
            TruncClase = TruncMonth('timestamp')
            formato_fecha = "%b %Y"

        datos_agrupados = lecturas.annotate(
            periodo=TruncClase
        ).values(
            'dispositivo__nombre', 'periodo'
        ).annotate(
            consumo_total=Sum('valor_flujo')
        ).order_by('periodo')
        
        # --- INICIO DE LA MODIFICACIÓN ---
        
        # 1. Procesamos los datos en una estructura anidada
        # { "Sensor 1": {"Nov 2025": 120, "Dic 2025": 150}, ... }
        labels_set = set()
        sensores_data_dict = {} 

        for item in datos_agrupados:
            sensor_nombre = item['dispositivo__nombre']
            label = item['periodo'].strftime(formato_fecha)
            labels_set.add(label)
            
            if sensor_nombre not in sensores_data_dict:
                sensores_data_dict[sensor_nombre] = {}
            
            sensores_data_dict[sensor_nombre][label] = item['consumo_total']

        # 2. Creamos una lista de etiquetas maestras ordenada
        labels = sorted(list(labels_set), key=lambda d: datetime.strptime(d.replace("Semana ", "") if agrupar_por == 'semana' else d, "%W, %Y" if agrupar_por == 'semana' else "%b %Y"))

        # 3. Construimos el JSON final
        # { "labels": ["Nov 2025", ...], "sensores": { "Sensor 1": [120, 0], ... } }
        sensores_data_final = {}
        for nombre_sensor, data_dict in sensores_data_dict.items():
            data_list = []
            for label in labels:
                data_list.append(data_dict.get(label, 0)) # 0 si no hay datos
            sensores_data_final[nombre_sensor] = data_list
        
        # Devolvemos una estructura que el frontend pueda iterar fácilmente
        return JsonResponse({
            'labels': labels, 
            'sensores': sensores_data_final
        })
    

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500, safe=False)
    


# Datos del MAPA
@login_required
def popup_lectura_latest(request, id_mqtt):
    """
    Vista que devuelve un fragmento de HTML con la lectura más reciente para HTMX.
    """
    # 1. Obtenemos el dispositivo del usuario actual y el id_mqtt
    dispositivo = get_object_or_404(
        Dispositivo, 
        usuario__usuario=request.user, 
        id_dispositivo_mqtt=id_mqtt
    )

    # 2. Obtenemos la última lectura del sensor (sin Subquery, es más simple aquí)
    ultima_lectura = LecturaSensor.objects.filter(
        dispositivo=dispositivo
    ).order_by('-timestamp').first()

    last_flow_value = ultima_lectura.valor_flujo if ultima_lectura else 0.0

    return render(request, 'sensores/popup_content.html', {
        'nombre': dispositivo.nombre or dispositivo.id_dispositivo_mqtt,
        'id_mqtt': id_mqtt,
        'last_flow_value': last_flow_value
    })