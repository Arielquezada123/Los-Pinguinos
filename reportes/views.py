from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from gestorUser.models import Usuario, Membresia, Organizacion
from sensores.models import Dispositivo, LecturaSensor
from django.db.models import Sum, Count
from django.db import transaction
from django.contrib import messages
from sensores.views import get_organizacion_actual
from django.utils import timezone
from .forms import TarifaForm, ReglaAlertaForm 
from .models import Alerta, Tarifa, Boleta, ReglaAlerta
from gestorUser.forms import LimiteMensualForm

# --- IMPORTS DE GRÁFICOS Y PDF ---
import io
import base64
import qrcode
import qrcode.image.svg
import barcode
from barcode.writer import SVGWriter
import matplotlib.pyplot as plt
import matplotlib
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML

# Configurar Matplotlib para trabajar sin pantalla
matplotlib.use('Agg')

# ==============================================================================
#  FUNCIONES AUXILIARES: Generan Imágenes SVG en Base64 (Infalible)
# ==============================================================================

def generar_grafico_historial(cliente):
    """
    Genera un gráfico de barras del consumo de los últimos 6 meses.
    Retorna: String Base64 de la imagen SVG.
    """
    # 1. Obtener datos (últimos 6 meses)
    boletas = Boleta.objects.filter(cliente=cliente).order_by('-ano', '-mes')[:6]
    boletas = sorted(list(boletas), key=lambda x: (x.ano, x.mes))

    # Si no hay historia, no devolvemos nada
    if not boletas:
        return None

    etiquetas = [f"{b.mes}/{str(b.ano)[2:]}" for b in boletas] # Ej: 11/25
    valores = [b.consumo_m3 for b in boletas]

    # 2. Configurar el gráfico (Tamaño ideal para la boleta)
    fig, ax = plt.subplots(figsize=(6, 2.5)) 
    
    # Barras en azul corporativo
    barras = ax.bar(etiquetas, valores, color='#021446', width=0.5)

    # Estilos limpios (sin bordes innecesarios)
    ax.set_title('Historial de Consumo Últimos 6 Meses (m³)', fontsize=9, color='#021446', weight='bold')
    ax.tick_params(axis='both', labelsize=7)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#ccc')
    ax.spines['bottom'].set_color('#ccc')
    
    # Etiqueta de valor sobre cada barra
    for bar in barras:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=6)

    # 3. Guardar como SVG en memoria
    buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format='svg', transparent=True)
    plt.close(fig)
    
    # 4. Convertir a Base64 para incrustar en HTML
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def generar_codigo_barras(boleta):
    """
    Genera el código de barras lineal para pago (Code128).
    Retorna: String Base64 de la imagen SVG.
    """
    # Identificador único para pagar
    codigo_valor = f"{boleta.id:06d}{boleta.monto_total}" 
    
    writer = SVGWriter()
    CODE = barcode.get_barcode_class('code128')
    code_img = CODE(codigo_valor, writer=writer)
    
    buffer = io.BytesIO()
    # Generamos solo las barras (sin texto abajo, el texto lo ponemos en HTML)
    code_img.write(buffer, options={"write_text": False, "quiet_zone": 1.0})
    
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

# ==============================================================================
#  VISTAS DEL SISTEMA
# ==============================================================================

@login_required
def reportes_pagina(request):
    if Membresia.objects.filter(usuario=request.user.usuario).exists():
        return redirect('empresa_inicio')
    usuario_actual = request.user.usuario
    alertas = Alerta.objects.filter(usuario=usuario_actual).order_by('-timestamp')
    return render(request, 'dashboard_reportes.html', {'alertas_list': alertas})

@login_required
def configuracion_tarifas_view(request):
    organizacion_actual = get_organizacion_actual(request.user.usuario)
    if not organizacion_actual: return redirect('post_login') 

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

    return render(request, 'reportes/configuracion_tarifas.html', {'form': form})

@login_required
def facturacion_view(request):
    try:
        membresia = Membresia.objects.get(usuario=request.user.usuario)
        organizacion_actual = membresia.organizacion
    except Membresia.DoesNotExist:
        return redirect('post_login')
         
    empresa = organizacion_actual
    try:
        tarifa_activa = organizacion_actual.tarifa 
        if not tarifa_activa: raise Tarifa.DoesNotExist
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
            if Boleta.objects.filter(cliente=cliente, mes=mes, ano=ano).exists():
                boletas_omitidas += 1
                continue
            
            lecturas = LecturaSensor.objects.filter(
                dispositivo__usuario=cliente,
                timestamp__year=ano, timestamp__month=mes
            ).order_by('timestamp').iterator()

            total_litros = 0.0
            prev_lectura = None
            for lectura_actual in lecturas:
                if prev_lectura:
                    duration_sec = (lectura_actual.timestamp - prev_lectura.timestamp).total_seconds()
                    if 0 < duration_sec <= 300:
                        total_litros += prev_lectura.valor_flujo * (duration_sec / 60.0)
                prev_lectura = lectura_actual
            
            consumo_m3 = total_litros / 1000.0
            
            if consumo_m3 <= tarifa_activa.limite_tramo_1:
                monto_consumo = consumo_m3 * tarifa_activa.valor_tramo_1
            else:
                monto_consumo = (tarifa_activa.limite_tramo_1 * tarifa_activa.valor_tramo_1) + \
                                ((consumo_m3 - tarifa_activa.limite_tramo_1) * tarifa_activa.valor_tramo_2)

            monto_neto = tarifa_activa.cargo_fijo + round(monto_consumo)
            monto_iva = round(monto_neto * tarifa_activa.iva)
            
            try:
                with transaction.atomic():
                    Boleta.objects.create(
                        empresa=empresa, cliente=cliente, tarifa_aplicada=tarifa_activa,
                        mes=mes, ano=ano, consumo_m3=consumo_m3,
                        monto_cargo_fijo=tarifa_activa.cargo_fijo,
                        monto_consumo_variable=round(monto_consumo),
                        monto_neto=monto_neto, monto_iva=monto_iva,
                        monto_total=monto_neto + monto_iva, estado_sii="Pendiente"
                    )
                    boletas_creadas += 1
            except Exception:
                boletas_omitidas += 1

        messages.success(request, f"Proceso completado: {boletas_creadas} creadas, {boletas_omitidas} omitidas.")
        return redirect('empresa_facturacion')

    periodos = Boleta.objects.filter(empresa=empresa).values('ano', 'mes').annotate(
        total=Sum('monto_total'), count=Count('id')).order_by('-ano', '-mes')
    return render(request, 'reportes/facturacion.html', {'periodos_facturados': periodos})

@login_required
def facturacion_detalle_mes_view(request, ano, mes):
    org = get_organizacion_actual(request.user.usuario)
    if not org: return redirect('post_login')
    boletas = Boleta.objects.filter(empresa=org, ano=ano, mes=mes).select_related('cliente__usuario')
    return render(request, 'reportes/facturacion_detalle_mes.html', {'boletas_del_mes': boletas, 'periodo_mes': mes, 'periodo_ano': ano})

@login_required
def ver_boleta_view(request, boleta_id):
    boleta = get_object_or_404(Boleta, id=boleta_id)
    usuario = request.user.usuario
    org = get_organizacion_actual(usuario)
    if not (boleta.cliente == usuario or boleta.empresa == org):
        messages.error(request, "Acceso denegado.")
        return redirect('post_login')
    return render(request, 'reportes/boleta_detalle.html', {'boleta': boleta})

@login_required
def cliente_lista_boletas_view(request):
    if Membresia.objects.filter(usuario=request.user.usuario).exists():
        return redirect('empresa_inicio')
    boletas = Boleta.objects.filter(cliente=request.user.usuario).order_by('-ano', '-mes')
    return render(request, 'reportes/cliente_lista_boletas.html', {'boletas_recibidas': boletas})

@login_required
def registrar_pago_view(request, boleta_id):
    boleta = get_object_or_404(Boleta, id=boleta_id)
    org = get_organizacion_actual(request.user.usuario)
    if not org or boleta.empresa != org:
        messages.error(request, "No tiene permisos.")
        return redirect('empresa_facturacion')

    if request.method == 'POST':
        boleta.estado_pago = Boleta.EstadoPago.PAGADO
        boleta.fecha_pago = timezone.now()
        boleta.metodo_pago = request.POST.get('metodo_pago', 'Efectivo')
        boleta.save()
        messages.success(request, f"Pago registrado Boleta #{boleta.id}")
        
    return redirect('empresa_boleta_detalle', boleta_id=boleta.id)

# --- REGLAS ---
@login_required
def reglas_lista_view(request):
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
    return render(request, 'reportes/reglas_lista.html', {'reglas': reglas, 'form_limite': form_limite})

@login_required
def reglas_crear_view(request):
    user = request.user.usuario
    if request.method == 'POST':
        form = ReglaAlertaForm(user, request.POST)
        if form.is_valid():
            r = form.save(commit=False)
            r.usuario = user
            r.save()
            return redirect('reglas_lista')
    else: form = ReglaAlertaForm(user)
    return render(request, 'reportes/reglas_form.html', {'form': form, 'titulo': 'Nueva Regla'})

@login_required
def reglas_editar_view(request, regla_id):
    user = request.user.usuario
    regla = get_object_or_404(ReglaAlerta, id=regla_id, usuario=user)
    if request.method == 'POST':
        form = ReglaAlertaForm(user, request.POST, instance=regla)
        if form.is_valid():
            form.save()
            return redirect('reglas_lista')
    else: form = ReglaAlertaForm(user, instance=regla)
    return render(request, 'reportes/reglas_form.html', {'form': form, 'titulo': 'Editar Regla'})

@login_required
def reglas_eliminar_view(request, regla_id):
    user = request.user.usuario
    regla = get_object_or_404(ReglaAlerta, id=regla_id, usuario=user)
    if request.method == 'POST':
        regla.delete()
        return redirect('reglas_lista')
    return render(request, 'reportes/reglas_confirm_delete.html', {'regla': regla})

# ==============================================================================
#  VISTA PRINCIPAL: GENERAR BOLETA (PDF)
# ==============================================================================

@login_required
def generar_y_enviar_boleta(request, boleta_id):
    boleta = get_object_or_404(Boleta, id=boleta_id)
    org = get_organizacion_actual(request.user.usuario)
    
    if not org or boleta.empresa != org:
        messages.error(request, "No tienes permiso.")
        return redirect('empresa_facturacion')

    try:
        # 1. QR (Timbre SII) - Formato SVG Base64
        texto_qr = f"<TED><RE>{boleta.empresa.rut_empresa}</RE><F>{boleta.id}</F><MNT>{boleta.monto_total}</MNT></TED>"
        factory = qrcode.image.svg.SvgImage
        img_qr = qrcode.make(texto_qr, image_factory=factory, box_size=5, border=1)
        buffer_qr = io.BytesIO()
        img_qr.save(buffer_qr)
        qr_b64 = base64.b64encode(buffer_qr.getvalue()).decode('utf-8')

        # 2. GRÁFICO DE BARRAS (Historial) - Formato SVG Base64
        grafico_b64 = generar_grafico_historial(boleta.cliente)

        # 3. CÓDIGO DE BARRAS (Pago) - Formato SVG Base64
        barcode_b64 = generar_codigo_barras(boleta)

        # 4. Generar PDF (Renderizamos Template HTML)
        context = {
            'boleta': boleta,
            'qr_b64': qr_b64,
            'grafico_b64': grafico_b64,
            'barcode_b64': barcode_b64 
        }
        html_string = render_to_string('reportes/boleta_pdf.html', context)
        pdf_file = HTML(string=html_string).write_pdf()

        # 5. Guardar Archivo
        filename = f"boleta_{boleta.id}_{boleta.mes}_{boleta.ano}.pdf"
        boleta.pdf_boleta.save(filename, ContentFile(pdf_file), save=True)

        # 6. Enviar Correo
        email_cliente = boleta.cliente.usuario.email
        subject = f"Boleta Disponible - {boleta.mes}/{boleta.ano}"
        body = f"Estimado cliente, adjuntamos su boleta. Total a pagar: ${boleta.monto_total}"
        
        email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [email_cliente])
        email.attach(filename, pdf_file, 'application/pdf')
        email.send()

        messages.success(request, f"Boleta #{boleta.id} enviada correctamente a {email_cliente}.")

    except Exception as e:
        messages.error(request, f"Error: {e}")
        print(f"Error detallado: {e}")

    return redirect('empresa_boleta_detalle', boleta_id=boleta.id)