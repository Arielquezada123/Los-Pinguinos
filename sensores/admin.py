from django.contrib import admin
from .models import Dispositivo, LecturaSensor

@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'id_dispositivo_mqtt', 'usuario')
    search_fields = ('nombre', 'id_dispositivo_mqtt', 'usuario__usuario__username')

@admin.register(LecturaSensor)
class LecturaSensorAdmin(admin.ModelAdmin):
    list_display = ('dispositivo', 'valor_flujo', 'timestamp')
    list_filter = ('dispositivo', 'timestamp')
    date_hierarchy = 'timestamp'