import json
import datetime
from django.utils import timezone
from django.db.models import Avg, Min
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.mail import send_mail
from django.conf import settings

from .models import Dispositivo, LecturaSensor
from reportes.models import Alerta, ReglaAlerta

class SensorService:
    @staticmethod
    def procesar_lectura(topic, payload):
        try:
            data = json.loads(payload)
            device_id_mqtt = data.get("sensor_id")
            flow_value = float(data.get("flujo", 0))

            if not device_id_mqtt:
                return

            try:
                dispositivo = Dispositivo.objects.get(id_dispositivo_mqtt=device_id_mqtt)
            except Dispositivo.DoesNotExist:
                return 

            LecturaSensor.objects.create(dispositivo=dispositivo, valor_flujo=flow_value)
            usuario = dispositivo.usuario
            SensorService._enviar_websocket(usuario, data)
            SensorService._verificar_reglas_usuario(usuario, dispositivo, flow_value)

        except Exception as e:
            print(f"   [ERROR SERVICE] {e}")

    @staticmethod
    def _enviar_websocket(usuario, data):
        channel_layer = get_channel_layer()
        grupo_cliente = f"sensores_{usuario.usuario.id}"
        async_to_sync(channel_layer.group_send)(grupo_cliente, {"type": "sensor_update", "data": data})
        
        if usuario.organizacion_admin:
            grupo_empresa = f"sensores_org_{usuario.organizacion_admin.id}"
            async_to_sync(channel_layer.group_send)(grupo_empresa, {"type": "sensor_update", "data": data})

    @staticmethod
    def _verificar_reglas_usuario(usuario, dispositivo, flujo_actual):
        """
        Consulta las reglas activas y verifica si alguna se ha roto.
        """
        ahora = timezone.localtime(timezone.now())
        hora_actual = ahora.time()
        dia_semana_actual = str(ahora.weekday()) 
        reglas = ReglaAlerta.objects.filter(
            usuario=usuario,
            activa=True
        ).filter(
            dispositivo=dispositivo  
        ) | ReglaAlerta.objects.filter(
            usuario=usuario,
            activa=True,
            dispositivo__isnull=True 
        )

        for regla in reglas:

            if dia_semana_actual not in regla.dias_semana:
                continue 

            if regla.hora_inicio <= regla.hora_fin:
                if not (regla.hora_inicio <= hora_actual <= regla.hora_fin):
                    continue
            else:
                if not (hora_actual >= regla.hora_inicio or hora_actual <= regla.hora_fin):
                    continue

            if flujo_actual > regla.flujo_maximo:
                

                if regla.duracion_minima > 0:
                    es_persistente = SensorService._verificar_persistencia(
                        dispositivo, regla.flujo_maximo, regla.duracion_minima
                    )
                    if not es_persistente:
                        continue 

                SensorService._disparar_alerta(usuario, dispositivo, regla, flujo_actual)

    @staticmethod
    def _verificar_persistencia(dispositivo, umbral, minutos):
        """
        Verifica si el flujo ha sido mayor al umbral durante los últimos X minutos.
        """
        tiempo_inicio = timezone.now() - datetime.timedelta(minutes=minutos)
        
        min_flujo = LecturaSensor.objects.filter(
            dispositivo=dispositivo,
            timestamp__gte=tiempo_inicio
        ).aggregate(Min('valor_flujo'))['valor_flujo__min']

        if min_flujo is None: 
            return False 
            
        return min_flujo > umbral

    @staticmethod
    def _disparar_alerta(usuario, dispositivo, regla, flujo_actual):
        """
        Crea la alerta y envía email si corresponde.
        No repetir la misma alerta activa
        """
        hace_rato = timezone.now() - datetime.timedelta(minutes=30)
        
        duplicada = Alerta.objects.filter(
            usuario=usuario,
            dispositivo=dispositivo,
            tipo='EXCESO', 
            mensaje__contains=regla.nombre,
            timestamp__gte=hace_rato
        ).exists()

        if duplicada:
            return

        mensaje_alerta = f"Regla '{regla.nombre}' rota. Flujo: {flujo_actual:.2f} L/min (Límite: {regla.flujo_maximo})."
        
        Alerta.objects.create(
            usuario=usuario,
            dispositivo=dispositivo,
            tipo='EXCESO',
            mensaje=mensaje_alerta
        )
        print(f"   !!! ALERTA REGLA '{regla.nombre}' !!!")

        if regla.enviar_email:
            try:
                send_mail(
                    subject=f"⚠️ Alerta de Agua: {regla.nombre}",
                    message=f"Hola {usuario.usuario.username},\n\nSe ha detectado una anomalía en el sensor {dispositivo.nombre}.\n\n{mensaje_alerta}\n\nIngresa al dashboard para ver más detalles.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[usuario.usuario.email],
                    fail_silently=True
                )
                print("   -> Email enviado.")
            except Exception as e:
                print(f"   -> Falló envío email: {e}")