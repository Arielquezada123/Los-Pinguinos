from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Usuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)

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
    
    direccion = models.CharField(
        "Dirección del Cliente", 
        max_length=255, 
        blank=True
    )
    
    # 2. Nuevo campo para el RUT del cliente
    rut_cliente = models.CharField(
        "RUT del Cliente", 
        max_length=12, 
        blank=True, 
        help_text="Ej: 12.345.678-9"
    )

    # 3. Nuevos campos solo para la EMPRESA
    rut_empresa = models.CharField(
        "RUT de la Empresa", 
        max_length=12, 
        blank=True, 
        help_text="Ej: 76.123.456-K"
    )
    direccion_empresa = models.CharField(
        "Dirección de la Empresa", 
        max_length=255, 
        blank=True
    )
    
    # --- FIN DE LA MODIFICACIÓN ---

    def __str__(self):
        return f"{self.usuario.username} ({self.get_rol_display()})"

# Esta señal se encarga de crear un usuario asociado cuando se crea un nuevo User
@receiver(post_save, sender=User)
def crear_usuario(sender, instance, created, **kwargs):
    if created:
        Usuario.objects.create(usuario=instance)
