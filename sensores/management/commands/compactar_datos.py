from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Avg, Max, Min, Count
from sensores.models import Dispositivo, LecturaSensor, LecturaDiaria
import datetime

class Command(BaseCommand):
    help = 'Compacta lecturas antiguas (> 90 días) en promedios diarios para ahorrar espacio.'

    def handle(self, *args, **options):
        dias_retencion = 90
        fecha_corte = timezone.now().date() - datetime.timedelta(days=dias_retencion)
        
        self.stdout.write(f"--- INICIANDO COMPACTACIÓN ---")
        self.stdout.write(f"Compactando datos anteriores al: {fecha_corte}")

        dispositivos = Dispositivo.objects.all()
        
        total_eliminados = 0
        total_compactados = 0

        for dispositivo in dispositivos:
            lecturas_viejas = LecturaSensor.objects.filter(
                dispositivo=dispositivo,
                timestamp__date__lte=fecha_corte
            ).order_by('timestamp')

            if not lecturas_viejas.exists():
                continue

            self.stdout.write(f"Procesando sensor: {dispositivo.nombre} ({dispositivo.id_dispositivo_mqtt})")
            fechas_a_procesar = lecturas_viejas.datetimes('timestamp', 'day')

            for fecha_dt in fechas_a_procesar:
                fecha = fecha_dt.date()
                qs_dia = lecturas_viejas.filter(timestamp__date=fecha)
                
                if not qs_dia.exists():
                    continue
                stats = qs_dia.aggregate(
                    promedio=Avg('valor_flujo'),
                    maximo=Max('valor_flujo'),
                    conteo=Count('id')
                )

                consumo_litros = 0
                lecturas_list = list(qs_dia)
                for i in range(1, len(lecturas_list)):
                    delta = (lecturas_list[i].timestamp - lecturas_list[i-1].timestamp).total_seconds()
                    if delta < 300: 
                        consumo_litros += lecturas_list[i-1].valor_flujo * (delta / 60)
                obj, created = LecturaDiaria.objects.get_or_create(
                    dispositivo=dispositivo,
                    fecha=fecha,
                    defaults={
                        'flujo_promedio': stats['promedio'] or 0,
                        'flujo_maximo': stats['maximo'] or 0,
                        'consumo_total': round(consumo_litros, 2),
                        'cantidad_lecturas': stats['conteo']
                    }
                )
                if created:
                    count_deleted, _ = qs_dia.delete()
                    total_eliminados += count_deleted
                    total_compactados += 1
                    self.stdout.write(f"   -> {fecha}: Compactadas {count_deleted} lecturas en 1 registro.")
                else:
                    self.stdout.write(f"   -> {fecha}: Ya estaba compactado. Se borran duplicados si quedan.")
                    qs_dia.delete()

        self.stdout.write(self.style.SUCCESS(f"--- FIN ---"))
        self.stdout.write(self.style.SUCCESS(f"Días compactados: {total_compactados}"))
        self.stdout.write(self.style.SUCCESS(f"Registros de DB liberados: {total_eliminados}"))