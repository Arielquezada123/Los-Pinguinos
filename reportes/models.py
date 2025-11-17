from django.db import models
from gestorUser.models import Usuario 
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
        return f"Alerta de {self.get_tipo_display()} para {self.usuario.username}"

    class Meta:
        ordering = ['-timestamp'] # Mostrar los reportes mas recientes


class Tarifa(models.Model):
    """
    Define las reglas de cobro para una empresa.
    Cumple con los requisitos de la SISS (cargo fijo, tramos).
    """
    empresa = models.OneToOneField(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol': 'EMPRESA'})
    # Cargo Fijo (SISS)
    cargo_fijo = models.PositiveIntegerField(default=3000, help_text="Monto fijo mensual en CLP")
    # Tarifas por Tramos (SISS) - en m³ (1m³ = 1000 Litros)
    limite_tramo_1 = models.FloatField(default=15, help_text="Límite del primer tramo en m³")
    valor_tramo_1 = models.PositiveIntegerField(default=500, help_text="Valor por m³ en Tramo 1 (CLP)")
    valor_tramo_2 = models.PositiveIntegerField(default=1000, help_text="Valor por m³ sobre el Tramo 1 (CLP)")
    
    # Impuestos (IVA)
    iva = models.FloatField(default=0.19, help_text="Porcentaje de IVA (Ej: 0.19 para 19%)")
    @property
    def iva_porcentaje(self):
        return int(self.iva * 100)

    def __str__(self):
        return f"Tarifas para {self.empresa.usuario.username}"

class Boleta(models.Model):
    """
    Representa una boleta generada, cumpliendo con SISS y SII.
    """
    empresa = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="boletas_emitidas", limit_choices_to={'rol': 'EMPRESA'})
    cliente = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name="boletas_recibidas", limit_choices_to={'rol': 'CLIENTE'})
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

    class Meta:
        # No puede haber dos boletas para el mismo cliente en el mismo mes/año
        unique_together = ('cliente', 'mes', 'ano')

    def __str__(self):
        return f"Boleta {self.folio_sii or self.id} - {self.cliente.usuario.username} ({self.mes}/{self.ano})"