from django.shortcuts import render, redirect 
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import LecturaSensor, Dispositivo 
from .forms import DispositivoForm 
import json
from django.db.models import Sum, F
from django.db.models.functions import TruncMonth, TruncWeek
from datetime import datetime
from django.utils.html import mark_safe
from django.db.models import OuterRef, Subquery, FloatField
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from gestorUser.forms import EmpresaCreaClienteForm 
from gestorUser.models import Usuario




@login_required
def historial_consumo(request):
    """
    API que devuelve las últimas 50 lecturas.
    Modificada para aceptar ?cliente_id=X
    """
    usuario_perfil = get_usuario_a_filtrar(request)
    
    try:
        lecturas = LecturaSensor.objects.filter(
            dispositivo__usuario=usuario_perfil # <-- MODIFICADO
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

            dispositivo = form.save(commit=False)
            dispositivo.usuario = request.user.usuario

            dispositivo.save()
            return redirect('post_login') 
    
    else:
        form = DispositivoForm()

    return render(request, 'dashboard_ingreso.html', {
        'form': form
    })

@login_required
def mapa_pagina_view(request):
    """
    Renderiza la página del mapa, pasando las ubicaciones y la ÚLTIMA LECTURA
    para evitar el estado de "espera" en los pop-ups.
    """
    
    # 1. Definir la subconsulta...
    ultima_lectura_qs = LecturaSensor.objects.filter(
        dispositivo=OuterRef('pk') 
    ).order_by('-timestamp')

    # 2. Anotar los dispositivos...
    dispositivos_con_ultima_lectura = Dispositivo.objects.filter(
        usuario__usuario=request.user,
        latitud__isnull=False, 
        longitud__isnull=False
    ).annotate(
        last_flow_value=Subquery(
            ultima_lectura_qs.values('valor_flujo')[:1],
            output_field=FloatField()
        )
    ).values('nombre', 'id_dispositivo_mqtt', 'latitud', 'longitud', 'last_flow_value')

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
    context = {
        'locations_json': locations_json,
        'OWM_API_KEY': settings.OWM_API_KEY
    }

    return render(request, 'dashboard_mapa.html', context) 

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

            # Sumamos el (Flujo * Tiempo) para obtener VOLUMEN
            # (valor_flujo L/min) * (5 seg / 60 seg/min) = Litros
            consumo_total=Sum(F('valor_flujo') / 12.0, output_field=FloatField())

        ).order_by('periodo')

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

    # 2. Obtenemos la última lectura del sensor
    ultima_lectura = LecturaSensor.objects.filter(
        dispositivo=dispositivo
    ).order_by('-timestamp').first()

    last_flow_value = ultima_lectura.valor_flujo if ultima_lectura else 0.0

    return render(request, 'sensores/popup_content.html', {
        'nombre': dispositivo.nombre or dispositivo.id_dispositivo_mqtt,
        'id_mqtt': id_mqtt,
        'last_flow_value': last_flow_value
    })

@login_required
def api_inicio_data(request):
    """
    API que devuelve el estado inicial de TODOS los sensores del usuario,
    incluyendo su última lectura registrada en la BD.
    """
    # 1. Subconsulta para obtener la última lectura
    ultima_lectura_qs = LecturaSensor.objects.filter(
        dispositivo=OuterRef('pk')
    ).order_by('-timestamp')

    # 2. Obtenemos todos los dispositivos del usuario y anotamos la última lectura
    dispositivos = Dispositivo.objects.filter(
        usuario__usuario=request.user
    ).annotate(
        last_flow_value=Subquery(
            ultima_lectura_qs.values('valor_flujo')[:1],
            output_field=FloatField()
        )
    )

    data_list = []
    for d in dispositivos:
        data_list.append({
            # Usamos el username del 'User' de Django
            'cliente_id': d.usuario.usuario.username,
            'sensor_id': d.id_dispositivo_mqtt,
            'flujo': d.last_flow_value if d.last_flow_value is not None else 0.0,
        })

    return JsonResponse(data_list, safe=False)






@login_required
def lista_sensores_view(request):
    """
    (READ) Muestra la galería de todos los sensores registrados 
    por el usuario.
    """
    sensores = Dispositivo.objects.filter(usuario__usuario=request.user)
    context = {
        'sensores': sensores
    }
    return render(request, 'sensores/dashboard_sensores.html', context)


@login_required
def editar_sensor_view(request, id_mqtt):
    """
    (UPDATE) Muestra el formulario para editar un sensor existente.
    """
    # Buscamos el dispositivo específico de ese usuario
    dispositivo = get_object_or_404(
        Dispositivo, 
        id_dispositivo_mqtt=id_mqtt, 
        usuario__usuario=request.user
    )
    
    if request.method == 'POST':
        # Si el formulario se envía, lo validamos con los datos nuevos
        form = DispositivoForm(request.POST, instance=dispositivo)
        if form.is_valid():
            form.save()
            return redirect('lista_sensores') 
    else:
        # Si es GET, mostramos el formulario con los datos existentes
        form = DispositivoForm(instance=dispositivo)

    context = {
        'form': form,
        'dispositivo': dispositivo
    }
    return render(request, 'sensores/dashboard_sensor_editar.html', context)


@login_required
def eliminar_sensor_view(request, id_mqtt):
    """
    (DELETE) Muestra la confirmación antes de borrar un sensor.
    """
    dispositivo = get_object_or_404(
        Dispositivo, 
        id_dispositivo_mqtt=id_mqtt, 
        usuario__usuario=request.user
    )
    
    if request.method == 'POST':
        dispositivo.delete()
        return redirect('lista_sensores')

    context = {
        'dispositivo': dispositivo
    }
    return render(request, 'sensores/dashboard_sensor_confirmar_borrado.html', context)

@login_required
def empresa_dashboard_view(request):
    """
    Muestra el panel de inicio para el rol EMPRESA.
    """
    if request.user.usuario.rol != 'EMPRESA':
        return redirect('post_login') 

    context = {
        'total_clientes': request.user.usuario.clientes_administrados.count()
    }
    return render(request, 'empresa/dashboard_empresa.html', context)


@login_required
def empresa_crear_cliente_view(request):
    """
    Vista para que la Empresa cree un nuevo Cliente y su primer dispositivo.
    """
    if request.user.usuario.rol != Usuario.Rol.EMPRESA:
        return redirect('post_login')

    if request.method == 'POST':
        form = EmpresaCreaClienteForm(request.POST)
        if form.is_valid():
            try:
                form.save(empresa_admin=request.user.usuario)
                return redirect('empresa_inicio') 
            except Exception as e:
                form.add_error(None, f"Ocurrió un error inesperado: {e}")
    else:
        form = EmpresaCreaClienteForm()

    return render(request, 'empresa/crear_cliente.html', {
        'form': form
    })

@login_required
def empresa_lista_clientes_view(request):
    """
    Muestra a la Empresa una tabla con todos los clientes
    que administra.
    """
    # Seguridad
    if request.user.usuario.rol != Usuario.Rol.EMPRESA:
        return redirect('post_login')

    # Obtenemos los clientes usando el 'related_name' que definimos en el modelo
    clientes_administrados = request.user.usuario.clientes_administrados.all()

    context = {
        'clientes': clientes_administrados
    }
    return render(request, 'empresa/lista_clientes.html', context)


@login_required
def empresa_ver_cliente_view(request, cliente_id):
    """
    Muestra el dashboard de consumo de un cliente específico
    a la empresa administradora.
    """

    if request.user.usuario.rol != Usuario.Rol.EMPRESA:
        return redirect('post_login')

    cliente = get_object_or_404(Usuario, id=cliente_id)
    if cliente.empresa_asociada != request.user.usuario:
        return redirect('empresa_inicio')

    context = {
        'cliente': cliente
    }
    return render(request, 'empresa/ver_cliente.html', context)

def get_usuario_a_filtrar(request):
    """
    Función de ayuda para determinar qué usuario filtrar en las APIs.
    """
    # Por defecto, filtramos por el usuario que hace la petición
    usuario_filtrado = request.user.usuario
    
    # Obtenemos el ID del cliente de la URL (si existe)
    cliente_id = request.GET.get('cliente_id')

    # Si el que pide es una EMPRESA y especificó un cliente_id...
    if request.user.usuario.rol == Usuario.Rol.EMPRESA and cliente_id:
        try:
            # Buscamos a ese cliente
            cliente = Usuario.objects.get(id=cliente_id)
            # ¡Seguridad! Verificamos que ese cliente pertenezca a la empresa
            if cliente.empresa_asociada == request.user.usuario:
                usuario_filtrado = cliente
        except Usuario.DoesNotExist:
            # Si el cliente no existe, no devolvemos nada
            pass
    
    return usuario_filtrado
@login_required
def api_inicio_data(request):
    """
    API que devuelve el estado inicial de los sensores.
    Modificada para aceptar ?cliente_id=X
    """
    # Obtenemos el perfil de usuario a filtrar (ya sea el propio o el cliente)
    usuario_perfil = get_usuario_a_filtrar(request)

    # El resto de la función usa 'usuario_perfil' en lugar de 'request.user'
    ultima_lectura_qs = LecturaSensor.objects.filter(dispositivo=OuterRef('pk')).order_by('-timestamp')
    dispositivos = Dispositivo.objects.filter(
        usuario=usuario_perfil # <-- MODIFICADO
    ).annotate(...)
    
    data_list = []
    for d in dispositivos:
        data_list.append({
            'cliente_id': d.usuario.usuario.username,
            'sensor_id': d.id_dispositivo_mqtt,
            'flujo': d.last_flow_value if d.last_flow_value is not None else 0.0,
            'is_initial_data': True
        })
    return JsonResponse(data_list, safe=False)