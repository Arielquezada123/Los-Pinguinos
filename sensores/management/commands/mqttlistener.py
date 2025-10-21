from django.core.management.base import BaseCommand
from sensores.models import Medicion
import paho.mqtt.client as mqtt
from django.utils import timezone

# Configuración del broker HiveMQ Cloud
MQTT_BROKER = "d9adaadca39e466da5cfc08719f42550.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "Miguel"
MQTT_PASSWORD = "Miguelgamer509"
MQTT_TOPICS = [("miagua/flujo", 0), ("miagua/consumo", 0)]

def on_connect(client, userdata, flags, rc):
    print("🔗 Conectado al broker HiveMQ Cloud (código:", rc, ")")
    client.subscribe(MQTT_TOPICS)

def on_message(client, userdata, msg):
    try:
        valor = float(msg.payload.decode())
        tipo = msg.topic.split("/")[-1]  # "flujo" o "consumo"

        Medicion.objects.create(
            tipo=tipo,
            valor=valor,
            fecha=timezone.now()
        )
        print(f"💾 Guardado {tipo}: {valor} L")
    except Exception as e:
        print("⚠️ Error al guardar medición:", e)

class Command(BaseCommand):
    help = "Escucha datos MQTT del ESP32 y los guarda en la base de datos"

    def handle(self, *args, **options):
        client = mqtt.Client()
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        client.tls_set()  # Conexión segura
        client.on_connect = on_connect
        client.on_message = on_message

        print("🚀 Iniciando escucha MQTT...")
        client.connect(MQTT_BROKER, MQTT_PORT)
        client.loop_forever()
