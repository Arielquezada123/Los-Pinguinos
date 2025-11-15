from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Alerta, Tarifa, Boleta
from gestorUser.models import Usuario
from sensores.models import Dispositivo, LecturaSensor
from django.db.models import Sum, F, FloatField, Count
from django.db import transaction
from django.contrib import messages
import datetime
from .forms import TarifaForm


@login_required
def reportes_pagina(request):
    
    alertas = Alerta.objects.filter(usuario=request.user.usuario)
    
    context = {
        'alertas_list': alertas
    }
    return render(request, 'dashboard_reportes.html', context)

@login_required
def configuracion_tarifas_view(request):
    """
    Permite a la empresa crear o actualizar sus tarifas de cobro.
    """
    if request.user.usuario.rol != Usuario.Rol.EMPRESA:
        return redirect('post_login')

    empresa = request.user.usuario
    
    # Usamos get_or_create para obtener la tarifa o crear una vacía
    tarifa_obj, created = Tarifa.objects.get_or_create(empresa=empresa)

    if request.method == 'POST':
        form = TarifaForm(request.POST, instance=tarifa_obj)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Tarifas actualizadas correctamente!')
            return redirect('empresa_facturacion') # Regresar al panel de facturación
    else:
        form = TarifaForm(instance=tarifa_obj)

    return render(request, 'reportes/configuracion_tarifas.html', {
        'form': form
    })


@login_required
def facturacion_view(request):
    """
    Motor de Facturación y página principal de gestión.
    (Versión con cálculo de consumo preciso)
    """
    if request.user.usuario.rol != Usuario.Rol.EMPRESA:
        return redirect('post_login')

    empresa = request.user.usuario
    try:
        tarifa_activa = Tarifa.objects.get(empresa=empresa)
    except Tarifa.DoesNotExist:
        messages.error(request, "Error: Debe configurar sus tarifas antes de poder facturar.")
        return redirect('empresa_configuracion_tarifas')

    if request.method == 'POST':
        mes = int(request.POST.get('mes'))
        ano = int(request.POST.get('ano'))
        clientes_a_facturar = empresa.clientes_administrados.all()
        boletas_creadas = 0
        boletas_omitidas = 0

        for cliente in clientes_a_facturar:
            boleta_existe = Boleta.objects.filter(cliente=cliente, mes=mes, ano=ano).exists()
            if boleta_existe:
                boletas_omitidas += 1
                continue
    
            #Obtenemos todas las lecturas del cliente para el mes, ordenadas.
            lecturas = LecturaSensor.objects.filter(
                dispositivo__usuario=cliente,
                timestamp__year=ano,
                timestamp__month=mes
            ).order_by('timestamp').iterator()

            total_litros = 0.0
            prev_lectura = None

            for lectura_actual in lecturas:
                if prev_lectura:
                    # 2. Calcular la duración (en segundos) desde la última lectura
                    duration_sec = (lectura_actual.timestamp - prev_lectura.timestamp).total_seconds()

                    # Si el tiempo es 0, negativo, o muy grande (ej. sensor se apagó 1 día),
                    # no podemos calcular el volumen de forma fiable.
                    # Asumimos un máximo de 5 minutos (300 seg) entre lecturas válidas.
                    if duration_sec <= 0 or duration_sec > 300:
                        prev_lectura = lectura_actual
                        continue

                    # 3. Convertir la duración a MINUTOS
                    duration_min = duration_sec / 60.0
                    
                    # 4. Calcular el volumen de este "tramo".
                    # Usamos el caudal (L/min) de la lectura anterior
                    # y lo multiplicamos por el tiempo (min) transcurrido.
                    # (Caudal * Tiempo = Volumen)
                    volumen_tramo = prev_lectura.valor_flujo * duration_min
                    total_litros += volumen_tramo
                
                prev_lectura = lectura_actual
            #Convertir Litros a Metros Cúbicos
            consumo_m3 = total_litros / 1000.0
            
            # 6. Aplicar Lógica de Tramos (SISS)
            monto_consumo = 0
            if consumo_m3 <= tarifa_activa.limite_tramo_1:
                monto_consumo = consumo_m3 * tarifa_activa.valor_tramo_1
            else:
                consumo_tramo_1 = tarifa_activa.limite_tramo_1
                consumo_tramo_2 = consumo_m3 - tarifa_activa.limite_tramo_1
                monto_consumo = (consumo_tramo_1 * tarifa_activa.valor_tramo_1) + \
                                (consumo_tramo_2 * tarifa_activa.valor_tramo_2)

            monto_consumo = round(monto_consumo)

            #Calcular Total (SISS + SII)
            monto_neto = tarifa_activa.cargo_fijo + monto_consumo
            monto_iva = round(monto_neto * tarifa_activa.iva)
            monto_total = monto_neto + monto_iva

            try:
                with transaction.atomic():
                    Boleta.objects.create(
                        empresa=empresa,
                        cliente=cliente,
                        tarifa_aplicada=tarifa_activa,
                        mes=mes,
                        ano=ano,
                        consumo_m3=consumo_m3,
                        monto_cargo_fijo=tarifa_activa.cargo_fijo,
                        monto_consumo_variable=monto_consumo,
                        monto_neto=monto_neto,
                        monto_iva=monto_iva,
                        monto_total=monto_total,
                        estado_sii="Pendiente"
                    )
                    boletas_creadas += 1
            except Exception as e:
                print(f"Error al crear boleta para {cliente}: {e}")
                boletas_omitidas += 1

        messages.success(request, f"Proceso completado: {boletas_creadas} boletas creadas. {boletas_omitidas} omitidas.")
        return redirect('empresa_facturacion')

    periodos_facturados = Boleta.objects.filter(empresa=empresa) \
        .values('ano', 'mes') \
        .annotate(
            total_facturado=Sum('monto_total'),
            cantidad_boletas=Count('id')
        ).order_by('-ano', '-mes')  

    context = {
        'periodos_facturados': periodos_facturados
    }
    return render(request, 'reportes/facturacion.html', context)


@login_required
def facturacion_detalle_mes_view(request, ano, mes):
    """
    Muestra el detalle (todas las boletas) de un periodo de
    facturación específico (ej: 11/2025).
    """
    if request.user.usuario.rol != Usuario.Rol.EMPRESA:
        return redirect('post_login')

    # Seguridad: Solo boletas de esta empresa
    boletas_del_mes = Boleta.objects.filter(
        empresa=request.user.usuario,
        ano=ano,
        mes=mes
    ).select_related('cliente__usuario') # Optimización: trae los datos del cliente

    context = {
        'boletas_del_mes': boletas_del_mes,
        'periodo_mes': mes,
        'periodo_ano': ano,
    }
    return render(request, 'reportes/facturacion_detalle_mes.html', context)