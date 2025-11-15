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
    list_display = ('empresa', 'cargo_fijo', 'valor_tramo_1', 'valor_tramo_2', 'iva')
    search_fields = ('empresa__usuario__username',)
    # Usamos fieldsets para organizar la edición
    fieldsets = (
        (None, {
            'fields': ('empresa',)
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
    list_display = ('id', 'cliente', 'empresa', 'mes', 'ano', 'consumo_m3', 'monto_total', 'estado_sii')
    list_filter = ('estado_sii', 'empresa', 'mes', 'ano')
    search_fields = ('cliente__usuario__username', 'folio_sii')
    
    # Hacemos que las boletas sean de solo lectura en el admin,
    # ya que no deben modificarse manualmente.
    def get_readonly_fields(self, request, obj=None):
        if obj: # Si el objeto ya existe, todos los campos son de solo lectura
            return [field.name for field in self.model._meta.fields]
        return []