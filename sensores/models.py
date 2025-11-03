
from django.db import models
from django.contrib.auth.models import User
from gestorUser.models import Usuario

class Dispositivo(models.Model):
    # Relaciona el dispositivo con un perfil de usuario
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="dispositivos")
    
    # Este es el ID que el dispositivo envía en el mensaje MQTT
    id_dispositivo_mqtt = models.CharField(max_length=100, unique=True, help_text="El ID único usado en los mensajes MQTT")
    
    # Un nombre amigable para que lo identifiques
    nombre = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.nombre} ({self.id_dispositivo_mqtt})"

class LecturaSensor(models.Model):
    # Cada lectura pertenece a un dispositivo
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name="lecturas")
    
    # El valor numérico que estamos midiendo
    valor_flujo = models.FloatField()
    
    # La fecha y hora en que se guardó el registro
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lectura de {self.dispositivo.id_dispositivo_mqtt} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-timestamp']