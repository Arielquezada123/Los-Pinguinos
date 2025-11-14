from django.contrib import admin
from .models import Usuario 


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    
    # Campos a mostrar en la lista principal
    list_display = ('usuario', 'rol', 'empresa_asociada', 'rut_cliente', 'rut_empresa')
    search_fields = ('usuario__username', 'direccion', 'rut_cliente', 'rut_empresa')
    list_filter = ('rol',)
    raw_id_fields = ('empresa_asociada',)

    def get_fieldsets(self, request, obj=None):
        if obj and obj.rol == Usuario.Rol.EMPRESA:
            return (
                (None, {'fields': ('usuario', 'rol')}),
                ('Datos de Facturación (Empresa)', {
                    'classes': ('wide',),
                    'fields': ('rut_empresa', 'direccion_empresa')
                }),
            )

        return (
            (None, {'fields': ('usuario', 'rol')}),
            ('Datos de Facturación (Cliente)', {
                'classes': ('wide',),
                'fields': ('direccion', 'rut_cliente')
            }),
            ('Jerarquía (Administración)', {
                'classes': ('wide',),
                'fields': ('empresa_asociada',)
            }),
        )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('usuario',)
        return ()