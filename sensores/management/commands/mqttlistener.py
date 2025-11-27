import json
import paho.mqtt.client as mqtt
import os
import django
import datetime 
import socket  # <--- Agregado para diagnóstico de red
import sys
from django.utils import timezone 

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "watermilimiter.settings")
django.setup()

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from sensores.models import Dispositivo, LecturaSensor
from reportes.models import Alerta
from gestorUser.models import Usuario 

channel_layer = get_channel_layer()

BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
BROKER_PORT = 1883

print(f"--- INICIANDO DIAGNÓSTICO DE CONEXIÓN ---")
print(f"Objetivo: {BROKER_HOST}:{BROKER_PORT}")

try:
    print(f"1. Intentando ping TCP a {BROKER_HOST}...")
    sock = socket.create_connection((BROKER_HOST, BROKER_PORT), timeout=3) # Timeout de 3 segundos
    sock.close()
    print(f"   [ÉXITO] El puerto {BROKER_PORT} está abierto y respondiendo.")
except socket.timeout:
    print(f"   [ERROR] Tiempo de espera agotado. El servidor no responde.")
    print("   -> Posible causa: Firewall bloqueando o IP incorrecta.")
    sys.exit(1)
except ConnectionRefusedError:
    print(f"   [ERROR] Conexión rechazada. No hay nada corriendo en el puerto {BROKER_PORT}.")
    print("   -> Posible causa: Mosquitto no está iniciado.")
    sys.exit(1)
except Exception as e:
    print(f"   [ERROR] Falló la conexión de red: {e}")
    sys.exit(1)


# --- FUNCIÓN AUXILIAR: Cálculo de Consumo ---
def calcular_consumo_mes_actual(usuario):
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

def on_connect(client, userdata, flags, rc):
    """Se ejecuta cuando el Broker responde al intento de conexión"""
    if rc == 0:
        print("2. [CONECTADO] Conexión exitosa con el Broker MQTT.")
        client.subscribe("sensores/flujo")
        print("   Suscribiéndose a 'sensores/flujo'...")
    else:
        print(f"2. [ERROR] El Broker rechazó la conexión. Código: {rc}")

def on_disconnect(client, userdata, rc):
    print("   [AVISO] Desconectado del Broker.")

def on_message(client, userdata, msg):
    try:
        print(f"-> Dato recibido: {msg.topic}")
        data = json.loads(msg.payload.decode())
        
        device_id_mqtt = data.get("sensor_id")
        flow_value = data.get("flujo")

        if not device_id_mqtt or flow_value is None:
            return
        
        try:
            dispositivo = Dispositivo.objects.get(id_dispositivo_mqtt=device_id_mqtt)
            LecturaSensor.objects.create(dispositivo=dispositivo, valor_flujo=flow_value)

            # Lógica de Alertas
            usuario = dispositivo.usuario
            if usuario.limite_consumo_mensual > 0:
                consumo = calcular_consumo_mes_actual(usuario)
                
                # Debug en vivo
                print(f"   Usuario: {usuario.usuario.username} | Límite: {usuario.limite_consumo_mensual} | Actual: {consumo:.2f}")

                if consumo > usuario.limite_consumo_mensual:
                    # Anti-spam: verificar si ya avisamos hoy
                    alerta_hoy = Alerta.objects.filter(
                        usuario=usuario,
                        tipo='EXCESO',
                        mensaje__contains="límite mensual",
                        timestamp__gte=timezone.now() - datetime.timedelta(hours=24)
                    ).exists()

                    if not alerta_hoy:
                        Alerta.objects.create(
                            usuario=usuario,
                            tipo='EXCESO',
                            mensaje=f"Límite superado: {int(consumo)} L (Máx: {usuario.limite_consumo_mensual} L)."
                        )
                        print("   !!! ALERTA CREADA !!!")

            # Enviar a WebSockets
            grupo = f"sensores_{usuario.usuario.id}"
            async_to_sync(channel_layer.group_send)(grupo, {"type": "sensor_update", "data": data})

        except Dispositivo.DoesNotExist:
            print(f"   Error: Sensor '{device_id_mqtt}' no registrado.")

    except Exception as e:
        print(f"   Error procesando mensaje: {e}")

# --- INICIO DEL CLIENTE ---
client = mqtt.Client()
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

print("3. Iniciando Loop MQTT...")
try:
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    client.loop_forever()
except Exception as e:
    print(f"Error fatal en MQTT: {e}")