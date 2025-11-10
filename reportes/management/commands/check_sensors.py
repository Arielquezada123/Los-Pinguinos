from django.core.management.base import BaseCommand
from sensores.models import Dispositivo
from reportes.models import Alerta
from django.utils import timezone
import datetime

class Command(BaseCommand):
    help = 'Revisa si los sensores están offline'

    def handle(self, *args, **options):
        sensores_offline = 0
        for dispositivo in Dispositivo.objects.all():
            ultima_lectura = dispositivo.lecturas.first() # Ya están ordenadas por timestamp desc
            
            if not ultima_lectura:
                continue # Ignorar sensores sin lecturas

            # Si la última lectura fue hace más de (ej.) 2 horas
            if (timezone.now() - ultima_lectura.timestamp) > datetime.timedelta(hours=2):
                # Crear alerta (si no hay ya una alerta reciente de OFFLINE para este)
                existe_alerta = Alerta.objects.filter(
                    dispositivo=dispositivo, 
                    tipo='OFFLINE', 
                    timestamp__gte=timezone.now() - datetime.timedelta(days=1)
                ).exists()
                
                if not existe_alerta:
                    Alerta.objects.create(
                        usuario=dispositivo.usuario,
                        dispositivo=dispositivo,
                        tipo='OFFLINE',
                        mensaje=f"No se reciben datos del sensor '{dispositivo.nombre}' hace más de 2 horas."
                    )
                    sensores_offline += 1
        
        self.stdout.write(self.style.SUCCESS(f'Revisión completada. {sensores_offline} sensores marcados como offline.'))