from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Usuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)

    # --- INICIO DE LA MODIFICACIÓN ---

    # 1. Definir los roles
    class Rol(models.TextChoices):
        CLIENTE = 'CLIENTE', 'Cliente Final'
        EMPRESA = 'EMPRESA', 'Empresa Distribuidora'

    rol = models.CharField(
        max_length=10,
        choices=Rol.choices,
        default=Rol.CLIENTE 
    )

    empresa_asociada = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL,
        null=True, blank=True,
        limit_choices_to={'rol': Rol.EMPRESA}, 
        related_name='clientes_administrados'
    )

    # 3. Campos para la dirección (necesarios para la boleta)
    direccion = models.CharField(max_length=255, blank=True)

    def __str__(self):

        return f"{self.usuario.username} ({self.get_rol_display()})"

# Esta señal se encarga de crear un usuario asociado cuando se crea un nuevo User
@receiver(post_save, sender=User)
def crear_usuario(sender, instance, created, **kwargs):
    if created:
        Usuario.objects.create(usuario=instance)
