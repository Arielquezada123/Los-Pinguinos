import paho.mqtt.client as mqtt
import os
import socket
import sys
from django.core.management.base import BaseCommand
from sensores.services import SensorService

class Command(BaseCommand):
    help = 'Listener MQTT ligero que delega a SensorService'

    def handle(self, *args, **options):
        BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
        BROKER_PORT = 1883
        
        self.stdout.write(self.style.SUCCESS(f"--- MQTT LISTENER ---"))
        self.stdout.write(f"Objetivo: {BROKER_HOST}:{BROKER_PORT}")

        try:
            sock = socket.create_connection((BROKER_HOST, BROKER_PORT), timeout=3)
            sock.close()
            self.stdout.write("   [RED] Socket OK.")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"   [RED] Advertencia de socket: {e}"))

        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:
            client = mqtt.Client() 

        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.on_disconnect = self.on_disconnect

        try:
            client.connect(BROKER_HOST, BROKER_PORT, 60)
            client.loop_forever()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fatal MQTT: {e}"))

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print("   [MQTT] Conectado. Suscribiendo...")
            client.subscribe("sensores/flujo")
        else:
            print(f"   [MQTT] Fallo de conexión: {rc}")

    def on_message(self, client, userdata, msg):
        SensorService.procesar_lectura(msg.topic, msg.payload.decode())
    def on_disconnect(self, client, userdata, disconnect_flags, reason_code=None, properties=None):
        print("   [MQTT] Desconectado. Reintentando...")
