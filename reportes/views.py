from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from gestorUser.models import Usuario, Membresia, Organizacion
from sensores.models import Dispositivo, LecturaSensor
from django.db.models import Sum, F, FloatField, Count
from django.db import transaction
from django.contrib import messages
import datetime
from sensores.views import get_organizacion_actual
from django.utils import timezone
from .forms import TarifaForm, ReglaAlertaForm 
from .models import Alerta, Tarifa, Boleta, ReglaAlerta
import io
import base64
import qrcode
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML
from gestorUser.forms import LimiteMensualForm

@login_required
def reportes_pagina(request):
    """
    Página de reportes para el CLIENTE.
    Muestra el historial de alertas y notificaciones.
    """
    if Membresia.objects.filter(usuario=request.user.usuario).exists():
        return redirect('empresa_inicio')

    usuario_actual = request.user.usuario

    alertas = Alerta.objects.filter(usuario=usuario_actual).order_by('-timestamp')
    
    context = {
        'alertas_list': alertas
    }
    return render(request, 'dashboard_reportes.html', context)

@login_required
def configuracion_tarifas_view(request):
    """
    Permite a la empresa crear o actualizar sus tarifas de cobro.
    CORREGIDO: Maneja correctamente la relación OneToOne desde Organizacion.
    """
    organizacion_actual = get_organizacion_actual(request.user.usuario)
    if not organizacion_actual:
        return redirect('post_login') 

    if organizacion_actual.tarifa:
        tarifa_obj = organizacion_actual.tarifa
    else:
        tarifa_obj = Tarifa.objects.create()
        organizacion_actual.tarifa = tarifa_obj
        organizacion_actual.save()

    if request.method == 'POST':
        form = TarifaForm(request.POST, instance=tarifa_obj)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Tarifas actualizadas correctamente!')
            return redirect('empresa_facturacion') 
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
    try:
        membresia = Membresia.objects.get(usuario=request.user.usuario)
        organizacion_actual = membresia.organizacion
    except Membresia.DoesNotExist:
        return redirect('post_login')
         
    empresa = organizacion_actual
    try:
        tarifa_activa = organizacion_actual.tarifa 
        if not tarifa_activa:
            raise Tarifa.DoesNotExist
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
            lecturas = LecturaSensor.objects.filter(
                dispositivo__usuario=cliente,
                timestamp__year=ano,
                timestamp__month=mes
            ).order_by('timestamp').iterator()

            total_litros = 0.0
            prev_lectura = None

            for lectura_actual in lecturas:
                if prev_lectura:
                    duration_sec = (lectura_actual.timestamp - prev_lectura.timestamp).total_seconds()
                    if duration_sec <= 0 or duration_sec > 300:
                        prev_lectura = lectura_actual
                        continue
                    duration_min = duration_sec / 60.0
                    volumen_tramo = prev_lectura.valor_flujo * duration_min
                    total_litros += volumen_tramo
                
                prev_lectura = lectura_actual
            consumo_m3 = total_litros / 1000.0
            monto_consumo = 0
            if consumo_m3 <= tarifa_activa.limite_tramo_1:
                monto_consumo = consumo_m3 * tarifa_activa.valor_tramo_1
            else:
                consumo_tramo_1 = tarifa_activa.limite_tramo_1
                consumo_tramo_2 = consumo_m3 - tarifa_activa.limite_tramo_1
                monto_consumo = (consumo_tramo_1 * tarifa_activa.valor_tramo_1) + \
                                (consumo_tramo_2 * tarifa_activa.valor_tramo_2)

            monto_consumo = round(monto_consumo)

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
    organizacion_actual = get_organizacion_actual(request.user.usuario)
    if not organizacion_actual:
        return redirect('post_login')

    boletas_del_mes = Boleta.objects.filter(
        empresa=organizacion_actual, 
        ano=ano,
        mes=mes
    ).select_related('cliente__usuario') 

    context = {
        'boletas_del_mes': boletas_del_mes,
        'periodo_mes': mes,
        'periodo_ano': ano,
    }
    return render(request, 'reportes/facturacion_detalle_mes.html', context)

@login_required
def ver_boleta_view(request, boleta_id):
    """
    Fase 3 (SISS): Muestra el detalle de una única boleta.
    (Permite acceso a Cliente y Empleado de Empresa)
    """
    boleta = get_object_or_404(Boleta, id=boleta_id)
    usuario_actual = request.user.usuario
    es_propietario = (boleta.cliente == usuario_actual)
    organizacion_actual = get_organizacion_actual(usuario_actual)
    es_administrador = (boleta.empresa == organizacion_actual)

    if not (es_propietario or es_administrador):
        messages.error(request, "No tiene permiso para ver esta boleta.")
        if organizacion_actual: # Si es empleado, lo mandamos a su panel
            return redirect('empresa_facturacion')
        else: # Si es cliente, lo mandamos al suyo
            return redirect('post_login')
    
    context = {
        'boleta': boleta
    }
    return render(request, 'reportes/boleta_detalle.html', context)

@login_required
def cliente_lista_boletas_view(request):
    """
    Muestra al Cliente (doméstico o de empresa)
    su historial de boletas emitidas.
    """
    if Membresia.objects.filter(usuario=request.user.usuario).exists():
        return redirect('empresa_inicio')

    boletas = Boleta.objects.filter(
        cliente=request.user.usuario
    ).order_by('-ano', '-mes')

    context = {
        'boletas_recibidas': boletas
    }
    return render(request, 'reportes/cliente_lista_boletas.html', context)

@login_required
def registrar_pago_view(request, boleta_id):
    """
    Permite a la empresa registrar manualmente el pago de una boleta.
    (Escenario A)
    """
    boleta = get_object_or_404(Boleta, id=boleta_id)
    #Seguridad: Solo empleados de la empresa emisora pueden cobrar
    organizacion_actual = get_organizacion_actual(request.user.usuario)

    if not organizacion_actual or boleta.empresa != organizacion_actual:
        messages.error(request, "No tiene permisos para gestionar pagos de esta boleta.")
        return redirect('empresa_facturacion')

    if request.method == 'POST':
        #Procesar el pago
        metodo = request.POST.get('metodo_pago', 'Efectivo')

        boleta.estado_pago = Boleta.EstadoPago.PAGADO
        boleta.fecha_pago = timezone.now()
        boleta.metodo_pago = metodo
        boleta.save()
        
        messages.success(request, f"Pago registrado correctamente para la Boleta #{boleta.id}")
        
    return redirect('empresa_boleta_detalle', boleta_id=boleta.id)

    
@login_required
def reglas_lista_view(request):
    """
    (R) Centro de Control de Seguridad:
    Muestra el Límite Global Mensual (editable) Y la lista de reglas personalizadas.
    """
    usuario = request.user.usuario
    
    if request.method == 'POST' and 'submit_limite_global' in request.POST:
        form_limite = LimiteMensualForm(request.POST, instance=usuario)
        if form_limite.is_valid():
            form_limite.save()
            messages.success(request, 'Límite Mensual Global actualizado correctamente.')
            return redirect('reglas_lista')
    else:
        form_limite = LimiteMensualForm(instance=usuario)
    reglas = ReglaAlerta.objects.filter(usuario=usuario).order_by('-activa', 'hora_inicio')

    context = {
        'reglas': reglas,
        'form_limite': form_limite
    }
    return render(request, 'reportes/reglas_lista.html', context)

@login_required
def reglas_crear_view(request):
    """(C) Crear nueva regla"""
    usuario = request.user.usuario
    if request.method == 'POST':
        # Pasamos 'usuario' al form para filtrar sensores
        form = ReglaAlertaForm(usuario, request.POST)
        if form.is_valid():
            regla = form.save(commit=False)
            regla.usuario = usuario # Asignar dueño
            regla.save()
            messages.success(request, 'Regla de seguridad creada correctamente.')
            return redirect('reglas_lista')
    else:
        form = ReglaAlertaForm(usuario)
    
    return render(request, 'reportes/reglas_form.html', {'form': form, 'titulo': 'Nueva Regla'})

@login_required
def reglas_editar_view(request, regla_id):
    """(U) Editar regla existente"""
    usuario = request.user.usuario
    # Aseguramos que la regla pertenezca al usuario (Seguridad)
    regla = get_object_or_404(ReglaAlerta, id=regla_id, usuario=usuario)
    
    if request.method == 'POST':
        form = ReglaAlertaForm(usuario, request.POST, instance=regla)
        if form.is_valid():
            form.save()
            messages.success(request, 'Regla actualizada.')
            return redirect('reglas_lista')
    else:
        form = ReglaAlertaForm(usuario, instance=regla)
    
    return render(request, 'reportes/reglas_form.html', {'form': form, 'titulo': 'Editar Regla'})

@login_required
def reglas_eliminar_view(request, regla_id):
    """(D) Borrar regla"""
    usuario = request.user.usuario
    regla = get_object_or_404(ReglaAlerta, id=regla_id, usuario=usuario)
    
    if request.method == 'POST':
        regla.delete()
        messages.success(request, 'Regla eliminada.')
        return redirect('reglas_lista')
    
    return render(request, 'reportes/reglas_confirm_delete.html', {'regla': regla})



@login_required
def generar_y_enviar_boleta(request, boleta_id):
    """
    Genera el PDF, lo guarda y lo envía por correo.
    """
    # 1. Obtener la boleta y validar permisos (Seguridad básica)
    boleta = get_object_or_404(Boleta, id=boleta_id)
    
    # Validar que quien aprieta el botón sea admin de la empresa emisora
    usuario_actual = request.user.usuario
    organizacion_actual = get_organizacion_actual(usuario_actual)
    
    if not organizacion_actual or boleta.empresa != organizacion_actual:
        messages.error(request, "No tienes permiso para gestionar esta boleta.")
        return redirect('empresa_facturacion')

    try:
        # 2. Generar el Código QR (Texto Plano Simulado)
        # Formato: <RUT Emisor> <Tipo Doc> <Folio> <Fecha> <Monto>
        texto_qr = f"RUT:{boleta.empresa.rut_empresa}|FOLIO:{boleta.id}|FECHA:{boleta.fecha_emision.strftime('%Y-%m-%d')}|TOTAL:{boleta.monto_total}"
        
        qr = qrcode.QRCode(version=1, box_size=5, border=1)
        qr.add_data(texto_qr)
        qr.make(fit=True)
        img_qr = qr.make_image(fill='black', back_color='white')
        
        # Convertir QR a Base64 para incrustarlo en el HTML sin guardar archivo temporal
        buffer_qr = io.BytesIO()
        img_qr.save(buffer_qr, format="PNG")
        qr_b64 = base64.b64encode(buffer_qr.getvalue()).decode()

        # 3. Renderizar HTML a PDF
        context = {
            'boleta': boleta,
            'qr_b64': qr_b64
        }
        html_string = render_to_string('reportes/boleta_pdf.html', context)
        
        # Generar bytes del PDF
        pdf_file = HTML(string=html_string).write_pdf()

        # 4. Guardar PDF en el modelo
        filename = f"boleta_{boleta.id}_{boleta.mes}_{boleta.ano}.pdf"
        # ContentFile permite guardar bytes directamente en un FileField
        boleta.pdf_boleta.save(filename, ContentFile(pdf_file), save=True)

        # 5. Enviar Correo Electrónico
        email_cliente = boleta.cliente.usuario.email
        subject = f"Su Boleta de Agua Disponible - {boleta.mes}/{boleta.ano}"
        body = f"""
        Estimado Cliente,
        
        Adjuntamos su boleta correspondiente al periodo {boleta.mes}/{boleta.ano}.
        
        Total a pagar: ${boleta.monto_total}
        
        Atentamente,
        Equipo {boleta.empresa.nombre}
        """
        
        email = EmailMessage(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [email_cliente],
        )
        # Adjuntar el PDF generado
        email.attach(filename, pdf_file, 'application/pdf')
        email.send()

        messages.success(request, f"Boleta #{boleta.id} generada y enviada a {email_cliente} correctamente.")

    except Exception as e:
        messages.error(request, f"Error al procesar la boleta: {e}")
        print(e)

    # Redirigir de vuelta al detalle de la boleta o lista
    return redirect('empresa_boleta_detalle', boleta_id=boleta.id)