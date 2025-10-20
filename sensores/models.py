# app: sensores/models.py
from django.db import models
from django.contrib.auth.models import User
from gestorUser.models import Usuario

class Sensor(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="sensores")
    id_sensor = models.CharField(max_length=50, unique=True)
    ubicacion = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.id_sensor} ({self.usuario})"

class Medicion(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name="mediciones")
    flujo = models.FloatField()
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sensor.id_sensor} - {self.flujo} L/s"
