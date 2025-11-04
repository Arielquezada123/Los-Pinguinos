# watermilimiter/sensores/models.py
from django.db import models
from django.contrib.auth.models import User
from gestorUser.models import Usuario

class Dispositivo(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="dispositivos")
    
    id_dispositivo_mqtt = models.CharField(max_length=100, unique=True, help_text="El ID único usado en los mensajes MQTT")
    
    nombre = models.CharField(max_length=100, blank=True)

    latitud = models.FloatField(null=True, blank=True)
    longitud = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} ({self.id_dispositivo_mqtt})"

class LecturaSensor(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name="lecturas")
    valor_flujo = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lectura de {self.dispositivo.id_dispositivo_mqtt} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-timestamp']