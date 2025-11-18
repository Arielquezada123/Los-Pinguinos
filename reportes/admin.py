from django.contrib import admin
from .models import Alerta, Tarifa, Boleta

@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'dispositivo', 'tipo', 'timestamp', 'leida')
    list_filter = ('tipo', 'leida', 'timestamp')
    search_fields = ('usuario__usuario__username', 'dispositivo__nombre')
    list_editable = ('leida',)

@admin.register(Tarifa)
class TarifaAdmin(admin.ModelAdmin):
    list_display = ('id', 'organizacion', 'cargo_fijo', 'valor_tramo_1', 'valor_tramo_2')
    search_fields = ('organizacion__nombre',)
    fieldsets = (
        (None, {
            'fields': () 
        }),
        ('Cargos (SISS)', {
            'fields': ('cargo_fijo', 'limite_tramo_1', 'valor_tramo_1', 'valor_tramo_2')
        }),
        ('Impuestos (SII)', {
            'fields': ('iva',)
        }),
    )

@admin.register(Boleta)
class BoletaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'empresa', 'mes', 'ano', 'monto_total', 'estado_sii')
    list_filter = ('estado_sii', 'empresa', 'mes', 'ano')
    search_fields = ('cliente__usuario__username', 'empresa__nombre')
    
    def get_readonly_fields(self, request, obj=None):
        if obj: 
            return [field.name for field in self.model._meta.fields]
        return []