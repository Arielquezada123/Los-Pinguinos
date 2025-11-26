from django.db import models
from gestorUser.models import Usuario, Organizacion
from sensores.models import Dispositivo

class Alerta(models.Model):
    
    TIPO_ALERTA = [
        ('FUGA', 'Posible Fuga Detectada'),
        ('EXCESO', 'Consumo Excesivo'),
        ('OFFLINE', 'Sensor Desconectado'),
        ('INFO', 'Resumen/Información'),
    ]

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="alertas")
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.SET_NULL, null=True, blank=True)
    
    tipo = models.CharField(max_length=10, choices=TIPO_ALERTA)
    mensaje = models.TextField(help_text="Descripción detallada de la alerta")
    timestamp = models.DateTimeField(auto_now_add=True)
    leida = models.BooleanField(default=False)

    def __str__(self):
        # CORRECCIÓN: Accedemos al User interno (.usuario.usuario.username)
        return f"Alerta de {self.get_tipo_display()} para {self.usuario.usuario.username}"

    class Meta:
        ordering = ['-timestamp']


class Tarifa(models.Model):
    cargo_fijo = models.PositiveIntegerField(default=3000, help_text="Monto fijo mensual en CLP")
    limite_tramo_1 = models.FloatField(default=15, help_text="Límite del primer tramo en m³")
    valor_tramo_1 = models.PositiveIntegerField(default=500, help_text="Valor por m³ en Tramo 1 (CLP)")
    valor_tramo_2 = models.PositiveIntegerField(default=1000, help_text="Valor por m³ sobre el Tramo 1 (CLP)")
    iva = models.FloatField(default=0.19, help_text="Porcentaje de IVA (ej: 0.19)")

    @property
    def iva_porcentaje(self):
        return int(self.iva * 100)

    def __str__(self):
        if hasattr(self, 'organizacion'):
             return f"Tarifas para {self.organizacion.nombre}"
        return f"Tarifa ID {self.id} (Sin asignar)"

class Boleta(models.Model):
    """
    Representa una boleta generada, cumpliendo con SISS y SII.
    """
    empresa = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="boletas_emitidas")
    cliente = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name="boletas_recibidas", limit_choices_to={'organizacion_admin__isnull': False})
    tarifa_aplicada = models.ForeignKey(Tarifa, on_delete=models.PROTECT)

    # Periodo de facturación
    mes = models.PositiveIntegerField()
    ano = models.PositiveIntegerField()
    fecha_emision = models.DateTimeField(auto_now_add=True)
    # Desglose SISS
    consumo_m3 = models.FloatField(default=0)
    monto_cargo_fijo = models.PositiveIntegerField()
    monto_consumo_variable = models.PositiveIntegerField()
    monto_subsidio = models.PositiveIntegerField(default=0)
    
    monto_neto = models.PositiveIntegerField()
    monto_iva = models.PositiveIntegerField()
    monto_total = models.PositiveIntegerField()
    
    # Cumplimiento SII
    estado_sii = models.CharField(max_length=50, default="Pendiente")
    folio_sii = models.CharField(max_length=100, blank=True, null=True)
    pdf_boleta = models.FileField(upload_to='boletas/', blank=True, null=True)
    
    class EstadoPago(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente de Pago'
        PAGADO = 'PAGADO', 'Pagado'
        VENCIDO = 'VENCIDO', 'Vencido'

    estado_pago = models.CharField(
        max_length=20,
        choices=EstadoPago.choices,
        default=EstadoPago.PENDIENTE
    )
    fecha_pago = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Pago Real")
    metodo_pago = models.CharField(
        max_length=50, 
        blank=True, 
        help_text="Ej: Transferencia, Efectivo, Cheque"
    )
    class Meta:
        # No puede haber dos boletas para el mismo cliente en el mismo mes/año
        unique_together = ('cliente', 'mes', 'ano')

    def __str__(self):
        return f"Boleta {self.folio_sii or self.id} - {self.cliente.usuario.username} ({self.mes}/{self.ano})"