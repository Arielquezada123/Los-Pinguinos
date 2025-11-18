from django.contrib import admin
from .models import Usuario, Organizacion, Membresia

@admin.register(Organizacion)
class OrganizacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rut_empresa', 'direccion_empresa', 'tarifa')
    search_fields = ('nombre', 'rut_empresa')
    raw_id_fields = ('tarifa',) 

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'organizacion_admin', 'rut_cliente', 'direccion') 
    search_fields = ('usuario__username', 'rut_cliente')
    list_filter = ('organizacion_admin',)
    fields = ('usuario', 'organizacion_admin', 'rut_cliente', 'direccion')
    readonly_fields = ('usuario',)
    raw_id_fields = ('organizacion_admin',) 
@admin.register(Membresia)
class MembresiaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'organizacion', 'rol_interno')
    list_filter = ('organizacion', 'rol_interno')
    raw_id_fields = ('usuario', 'organizacion')