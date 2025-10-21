from django.db import models

class Medicion(models.Model):
    tipo = models.CharField(max_length=50)  # flujo o consumo
    valor = models.FloatField()
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo}: {self.valor} L ({self.fecha.strftime('%H:%M:%S')})"
