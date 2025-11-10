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