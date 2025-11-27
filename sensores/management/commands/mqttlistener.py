import json
import paho.mqtt.client as mqtt
import os
import socket
import sys
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import datetime

from sensores.models import Dispositivo, LecturaSensor
from reportes.models import Alerta
from gestorUser.models import Usuario

class Command(BaseCommand):
    help = 'Inicia el listener MQTT para recibir datos de sensores y guardarlos en la BD'

    def handle(self, *args, **options):

        BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mosquitto")
        BROKER_PORT = 1883
        
        self.stdout.write(self.style.SUCCESS(f"--- INICIANDO LISTENER MQTT (V2) ---"))
        self.stdout.write(f"Objetivo: {BROKER_HOST}:{BROKER_PORT}")

        self.stdout.write("1. Verificando conectividad TCP...")
        try:
            sock = socket.create_connection((BROKER_HOST, BROKER_PORT), timeout=5)
            sock.close()
            self.stdout.write(self.style.SUCCESS(f"   [RED] ¡Éxito! El puerto {BROKER_PORT} en {BROKER_HOST} está abierto."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   [RED] Advertencia: No se pudo conectar al socket ({e}). MQTT intentará reconectar..."))

        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:

            client = mqtt.Client()

        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.on_message = self.on_message

        try:
            self.stdout.write("2. Conectando al Broker MQTT...")
            client.connect(BROKER_HOST, BROKER_PORT, 60)
            self.stdout.write(self.style.SUCCESS("3. [SISTEMA] Iniciando bucle infinito de escucha..."))
            client.loop_forever()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fatal iniciando MQTT: {e}"))

    def on_connect(self, client, userdata, flags, rc, properties=None):
        """
        Se ejecuta cuando el Broker responde al intento de conexión.
        (Firma compatible con Paho MQTT v2: 5 argumentos)
        """
        if rc == 0:
            print("   [MQTT] Conectado exitosamente.")
            client.subscribe("sensores/flujo")
            print("   [MQTT] Suscrito al tema 'sensores/flujo'")
        else:
            print(f"   [MQTT] Error de conexión. Código de retorno: {rc}")

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        """
        Se ejecuta cuando se pierde la conexión.
        """
        print("   [MQTT] Desconectado del Broker. Intentando reconexión automática...")

    def on_message(self, client, userdata, msg):
        """
        Se ejecuta cada vez que llega un mensaje al tema suscrito.
        """
        try:
            payload_str = msg.payload.decode()
            data = json.loads(payload_str)
            
            device_id_mqtt = data.get("sensor_id")
            flow_value = data.get("flujo")

            if not device_id_mqtt or flow_value is None:
                return
            
            channel_layer = get_channel_layer()

            try:

                dispositivo = Dispositivo.objects.get(id_dispositivo_mqtt=device_id_mqtt)
                LecturaSensor.objects.create(dispositivo=dispositivo, valor_flujo=flow_value)
                
                usuario = dispositivo.usuario
                
                grupo_cliente = f"sensores_{usuario.usuario.id}"
                async_to_sync(channel_layer.group_send)(
                    grupo_cliente, 
                    {"type": "sensor_update", "data": data}
                )

                if usuario.organizacion_admin:
                    grupo_empresa = f"sensores_org_{usuario.organizacion_admin.id}"
                    async_to_sync(channel_layer.group_send)(
                        grupo_empresa, 
                        {"type": "sensor_update", "data": data}
                    )
                if usuario.limite_consumo_mensual > 0:
                    self.verificar_alertas(usuario)

            except Dispositivo.DoesNotExist:
                print(f"   [BD] Ignorado: El sensor '{device_id_mqtt}' no está registrado en el sistema.")

        except Exception as e:
            print(f"   [ERROR] Procesando mensaje: {e}")


    def verificar_alertas(self, usuario):
        """
        Calcula si el usuario superó su límite mensual y genera una alerta.
        """
        try:
            consumo_actual = self.calcular_consumo_mes_actual(usuario)
            
            if consumo_actual > usuario.limite_consumo_mensual:
                alerta_reciente = Alerta.objects.filter(
                    usuario=usuario,
                    tipo='EXCESO',
                    mensaje__contains="límite mensual",
                    timestamp__gte=timezone.now() - datetime.timedelta(hours=24)
                ).exists()

                if not alerta_reciente:
                    Alerta.objects.create(
                        usuario=usuario,
                        tipo='EXCESO',
                        mensaje=f"Límite mensual superado. Consumo: {int(consumo_actual)} L (Máx: {usuario.limite_consumo_mensual} L)."
                    )
                    print(f"   [ALERTA] Generada notificación de exceso para {usuario}")

        except Exception as e:
            print(f"   [ERROR] Falló la verificación de alertas: {e}")

    def calcular_consumo_mes_actual(self, usuario):
        """
        Calcula el consumo acumulado del mes en curso.
        """
        ahora = timezone.now()
        lecturas = LecturaSensor.objects.filter(
            dispositivo__usuario=usuario,
            timestamp__year=ahora.year,
            timestamp__month=ahora.month
        ).order_by('timestamp').iterator()

        total_litros = 0.0
        prev_lectura = None

        for lectura_actual in lecturas:
            if prev_lectura:
                duration_sec = (lectura_actual.timestamp - prev_lectura.timestamp).total_seconds()
                if 0 < duration_sec <= 300:
                    duration_min = duration_sec / 60.0
                    volumen_tramo = prev_lectura.valor_flujo * duration_min
                    total_litros += volumen_tramo
            prev_lectura = lectura_actual
        
        return total_litros