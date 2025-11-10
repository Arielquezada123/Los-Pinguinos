from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Usuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    limite_consumo_mensual = models.FloatField(null=True, blank=True)
    def __str__(self):
        return self.usuario.username

# Esta señal se encarga de crear un usuario asociado cuando se crea un nuevo User
@receiver(post_save, sender=User)
def crear_usuario(sender, instance, created, **kwargs):
    if created:
        Usuario.objects.create(usuario=instance)
