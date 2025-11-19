from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from .models import LecturaSensor, Dispositivo 
from .forms import DispositivoForm, LimiteDispositivoForm   
import json
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils.html import mark_safe
from django.db.models import OuterRef, Subquery, FloatField
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.forms import modelformset_factory
from django.contrib import messages
from gestorUser.forms import EmpresaCreaClienteForm, LimiteMensualForm 
from gestorUser.models import Usuario, Membresia, Organizacion
from django.db.models import Count, Max,  Sum, F
from django.utils import timezone
from datetime import timedelta, datetime
from django.conf import settings



@login_required
def historial_consumo(request):
    """
    API que devuelve las últimas 50 lecturas.
    Modificada para aceptar ?cliente_id=X
    """

    usuario_perfil = get_usuario_a_filtrar(request)
    
    try:
        lecturas = LecturaSensor.objects.filter(
            dispositivo__usuario=usuario_perfil 
        ).order_by('-timestamp')[:50] 

        data = [
            {
                "sensor_nombre": lectura.dispositivo.nombre or lectura.dispositivo.id_dispositivo_mqtt,
                "valor": lectura.valor_flujo,
                "timestamp": lectura.timestamp.isoformat()
            }
            for lectura in lecturas
        ]
        
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


@login_required
def popup_lectura_latest(request, id_mqtt):
    """
    Vista que devuelve un fragmento de HTML con la lectura más reciente para HTMX/Fetch.
    Corregida para usar Membresia y Organizacion.
    """

    dispositivo = get_object_or_404(
        Dispositivo, 
        id_dispositivo_mqtt=id_mqtt
    )

    es_dueño_cliente = (dispositivo.usuario.usuario == request.user)
    es_empresa_admin = False
    org_del_cliente = dispositivo.usuario.organizacion_admin 

    if org_del_cliente:

        es_empresa_admin = Membresia.objects.filter(
            usuario=request.user.usuario,
            organizacion=org_del_cliente
        ).exists()

    if not (es_dueño_cliente or es_empresa_admin):
        return HttpResponse("Acceso denegado.", status=403)

    ultima_lectura = LecturaSensor.objects.filter(
        dispositivo=dispositivo
    ).order_by('-timestamp').first()

    last_flow_value = ultima_lectura.valor_flujo if ultima_lectura else 0.0

    context = {
        'nombre': dispositivo.nombre or dispositivo.id_dispositivo_mqtt,
        'id_mqtt': id_mqtt,
        'last_flow_value': last_flow_value,
        'cliente_username': dispositivo.usuario.usuario.get_full_name(),
        'cliente_direccion': dispositivo.usuario.direccion 
    }

    return render(request, 'sensores/popup_content.html', context)



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
def configuracion_pagina(request):
    # Preparamos el FormSet para los dispositivos del usuario
    DispositivoFormSet = modelformset_factory(
        Dispositivo, 
        form=LimiteDispositivoForm, 
        extra=0 # No mostrar formularios vacíos
    )

    if request.method == 'POST':
        # Identificar qué formulario se envió
        if 'submit_limite_mensual' in request.POST:
            limite_mensual_form = LimiteMensualForm(request.POST, instance=request.user.usuario)
            dispositivo_formset = DispositivoFormSet(queryset=Dispositivo.objects.filter(usuario=request.user.usuario))

            if limite_mensual_form.is_valid():
                limite_mensual_form.save()
                messages.success(request, 'Límite mensual actualizado.')
                return redirect('configuracion_pagina')

        elif 'submit_limites_dispositivos' in request.POST:
            limite_mensual_form = LimiteMensualForm(instance=request.user.usuario)
            dispositivo_formset = DispositivoFormSet(request.POST, queryset=Dispositivo.objects.filter(usuario=request.user.usuario))

            if dispositivo_formset.is_valid():
                dispositivo_formset.save()
                messages.success(request, 'Límites de dispositivos actualizados.')
                return redirect('configuracion_pagina')

    else:
        # Petición GET: Instanciar formularios
        limite_mensual_form = LimiteMensualForm(instance=request.user.usuario)
        dispositivo_formset = DispositivoFormSet(queryset=Dispositivo.objects.filter(usuario=request.user.usuario))

    context = {
        'limite_mensual_form': limite_mensual_form,
        'dispositivo_formset': dispositivo_formset
    }
    return render(request, 'dashboard_configuracion.html', context)


def get_organizacion_actual(usuario_perfil):
    """
    Obtiene la Organización a la que pertenece un empleado.
    """
    try:
        membresia = Membresia.objects.get(usuario=usuario_perfil)
        return membresia.organizacion
    except Membresia.DoesNotExist:
        return None
        
@login_required
def empresa_dashboard_view(request):
    """
    Muestra el panel de inicio para el rol EMPRESA.
    (Versión corregida con lógica de Membresia)
    """
    organizacion_actual = get_organizacion_actual(request.user.usuario)
    
    if not organizacion_actual:
        return redirect('post_login')


    clientes_de_la_empresa = organizacion_actual.clientes_administrados.all()
    dispositivos_de_la_empresa = Dispositivo.objects.filter(
        usuario__in=clientes_de_la_empresa
    )

    una_hora_atras = timezone.now() - timedelta(hours=1)
    sensores_offline = dispositivos_de_la_empresa.annotate(
        ultima_lectura=Max('lecturas__timestamp')
    ).filter(
        ultima_lectura__lt=una_hora_atras
    ).distinct()

    clientes_offline_ids = sensores_offline.values_list('usuario_id', flat=True).distinct()
    clientes_offline = Usuario.objects.filter(id__in=clientes_offline_ids)

    context = {
        'total_clientes': clientes_de_la_empresa.count(),
        'total_sensores': dispositivos_de_la_empresa.count(),
        'total_sensores_offline': sensores_offline.count(),
        'total_clientes_offline': clientes_offline.count(),
        'sensores_offline_list': sensores_offline,
        'clientes_administrados': clientes_de_la_empresa, 
        'clientes_offline_list': clientes_offline,
    }
    return render(request, 'empresa/dashboard_empresa.html', context)


@login_required
def empresa_crear_cliente_view(request):
    """
    Vista para que la Empresa cree un nuevo Cliente y su primer dispositivo.
    """
    organizacion_actual = get_organizacion_actual(request.user.usuario)
    if not organizacion_actual:
        return redirect('post_login')

    if request.method == 'POST':
        form = EmpresaCreaClienteForm(request.POST)
        if form.is_valid():
            try:
                form.save(request=request, organizacion_actual=organizacion_actual)
                messages.success(request, f"Cliente {form.cleaned_data['first_name']} creado. Se ha enviado un email de activación.")
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
    organizacion_actual = get_organizacion_actual(request.user.usuario)
    if not organizacion_actual:
        return redirect('post_login')
    
    clientes_administrados = organizacion_actual.clientes_administrados.all()

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
    organizacion_actual = get_organizacion_actual(request.user.usuario)
    if not organizacion_actual:
        return redirect('post_login')
    
    cliente = get_object_or_404(Usuario, id=cliente_id)
    if cliente.organizacion_admin != organizacion_actual:
        return redirect('empresa_inicio')

    lecturas = LecturaSensor.objects.filter(
        dispositivo__usuario=cliente # Filtrar por el objeto cliente (Usuario)
    )
    datos_agregados = lecturas.annotate(
        periodo=TruncMonth('timestamp')
    ).values(
        'periodo'
    ).annotate(
        consumo_total_m3=Sum(F('valor_flujo') / 12.0 / 1000.0, output_field=FloatField()) # Dividir por 1000 para m3
    ).order_by('periodo')
    etiquetas_mes = [item['periodo'].strftime("%b %Y") for item in datos_agregados]
    valores_consumo = [item['consumo_total_m3'] for item in datos_agregados]
    context = {
        'cliente': cliente,
        'etiquetas_grafico_json': mark_safe(json.dumps(etiquetas_mes)),
        'valores_grafico_json': mark_safe(json.dumps(valores_consumo)),
    }
    return render(request, 'empresa/ver_cliente.html', context)

@login_required
def empresa_mapa_view(request):
    """
    Renderiza un mapa general con TODOS los dispositivos
    de TODOS los clientes administrados por la empresa.
    """
    organizacion_actual = get_organizacion_actual(request.user.usuario)
    if not organizacion_actual:
        return redirect('post_login')

    clientes_administrados = organizacion_actual.clientes_administrados.all()
    
    dispositivos_de_clientes = Dispositivo.objects.filter(
        usuario__in=clientes_administrados,
        latitud__isnull=False, 
        longitud__isnull=False
    )

    #Reutilizamos la lógica de Subquery para obtener la última lectura de CADA uno
    ultima_lectura_qs = LecturaSensor.objects.filter(
        dispositivo=OuterRef('pk')
    ).order_by('-timestamp')

    dispositivos_con_lectura = dispositivos_de_clientes.annotate(
        last_flow_value=Subquery(
            ultima_lectura_qs.values('valor_flujo')[:1],
            output_field=FloatField()
        )
    ).values('nombre', 'id_dispositivo_mqtt', 'latitud', 'longitud', 'last_flow_value')

    #Serializamos a JSON (igual que en 'mapa_pagina_view')
    locations_list = [
        {
            'nombre': d['nombre'] or d['id_dispositivo_mqtt'],
            'id_mqtt': d['id_dispositivo_mqtt'], 
            'lat': d['latitud'],
            'lon': d['longitud'],
            'last_value': d['last_flow_value'] if d['last_flow_value'] is not None else 0.0,
        }
        for d in dispositivos_con_lectura
    ]
    
    locations_json = mark_safe(json.dumps(locations_list))

    return render(request, 'empresa/mapa_general.html', {
        'locations_json': locations_json,
        'OWM_API_KEY': settings.OWM_API_KEY
    })


def get_usuario_a_filtrar(request):
    """
    Función de ayuda para determinar qué usuario filtrar en las APIs.
    """
    usuario_filtrado = request.user.usuario
    cliente_id = request.GET.get('cliente_id')
    try:
        membresia = Membresia.objects.get(usuario=usuario_filtrado)
        es_empleado = True
        mi_organizacion = membresia.organizacion
    except Membresia.DoesNotExist:
        es_empleado = False
        mi_organizacion = None

    if es_empleado and cliente_id:
        try:
            cliente = Usuario.objects.get(id=cliente_id)
            if cliente.organizacion_admin == mi_organizacion:
                usuario_filtrado = cliente
        except Usuario.DoesNotExist:
            pass

    return usuario_filtrado

@login_required
def api_inicio_data(request):
    """
    API que devuelve el estado inicial de los sensores.
    Modificada para aceptar
    """
    usuario_perfil = get_usuario_a_filtrar(request) 

    ultima_lectura_qs = LecturaSensor.objects.filter(
        dispositivo=OuterRef('pk')
    ).order_by('-timestamp')

    dispositivos = Dispositivo.objects.filter(
        usuario=usuario_perfil
    ).annotate(
        last_flow_value=Subquery(
            ultima_lectura_qs.values('valor_flujo')[:1],
            output_field=FloatField()
        )
    )
    data_list = []
    for d in dispositivos:
        lecturas_recientes = LecturaSensor.objects.filter(dispositivo=d).order_by('-timestamp')[:30]
        valores_historial = [l.valor_flujo for l in lecturas_recientes[::-1]]
        last_value = valores_historial[-1] if valores_historial else 0.0
        data_list.append({
            'cliente_id': d.usuario.usuario.username,
            'sensor_id': d.id_dispositivo_mqtt,
            'historial_flujo': valores_historial,
            'flujo': d.last_flow_value if d.last_flow_value is not None else 0.0,
            'is_initial_data': True
        })
    return JsonResponse(data_list, safe=False)
