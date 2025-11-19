from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Organizacion(models.Model):
    """
    Representa a la Empresa (ej. "Glaciar").
    Almacena los datos de facturación y empleados.
    """
    nombre = models.CharField(max_length=200, unique=True)
    rut_empresa = models.CharField("RUT de la Empresa", max_length=12, blank=True)
    direccion_empresa = models.CharField("Dirección de la Empresa", max_length=255, blank=True)
    
    tarifa = models.OneToOneField(
        'reportes.Tarifa', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name="organizacion"
    )

    def __str__(self):
        return self.nombre

class Usuario(models.Model):
    """
    Representa el perfil de una PERSONA.
    Puede ser un Cliente Doméstico o un Cliente de Empresa.
    (Los empleados se manejan por Membresia)
    """

    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    limite_consumo_mensual = models.PositiveIntegerField(default=10000,help_text="Límite de consumo mensual total en Litros")
    organizacion_admin = models.ForeignKey(
        Organizacion, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name="clientes_administrados"
    )

    rut_cliente = models.CharField("RUT del Cliente", max_length=12, blank=True)
    direccion = models.CharField("Dirección del Cliente", max_length=255, blank=True)
    def __str__(self):
        return self.usuario.username

class Membresia(models.Model):
    """
    vincula un Usuario (persona) a una Organizacion (empresa)
    y le da un rol de empleado.
    """
    class Rol(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        EMPLEADO = 'EMPLEADO', 'Empleado' 

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="membresias")
    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="miembros")
    rol_interno = models.CharField(max_length=20, choices=Rol.choices, default=Rol.EMPLEADO)

    class Meta:
        unique_together = ('usuario', 'organizacion')

    def __str__(self):
        return f"{self.usuario.usuario.username} es {self.get_rol_interno_display()} de {self.organizacion.nombre}"
        
@receiver(post_save, sender=User)
def crear_usuario(sender, instance, created, **kwargs):
    if created:
        Usuario.objects.create(usuario=instance)