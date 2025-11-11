from django.contrib import admin
from .models import Usuario 


class UsuarioAdmin(admin.ModelAdmin):
    
    list_display = ('usuario', 'rol', 'empresa_asociada', 'direccion')
    fields = ('usuario', 'rol', 'empresa_asociada', 'direccion')
    readonly_fields = ('usuario',)

    list_filter = ('rol', 'empresa_asociada')
    search_fields = ('usuario__username', 'direccion')
    raw_id_fields = ('empresa_asociada',)

admin.site.register(Usuario, UsuarioAdmin)