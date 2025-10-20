# sensores/management/commands/mqttlistener.py
import json
import time
import paho.mqtt.client as mqtt
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Escucha mensajes MQTT y los reenvía por WebSockets"

    def handle(self, *args, **kwargs):
        client = mqtt.Client()
        client.connect("localhost", 1883)

        channel_layer = get_channel_layer()

        def on_message(client, userdata, msg):
            try:
                data = json.loads(msg.payload.decode("utf-8"))
                print(f"📩 Recibido: {data}")

                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        "sensores_group",
                        {
                            "type": "enviar_dato",
                            "data": data,
                        }
                    )
                else:
                    print("⚠️ Channel layer no disponible")

            except Exception as e:
                print(f"❌ Error procesando mensaje: {e}")

        client.subscribe("sensores/flujo")
        client.on_message = on_message
        print("🟢 MQTT listener iniciado...")
        client.loop_forever()
