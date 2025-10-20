import json
import paho.mqtt.client as mqtt
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "watermilimiter.settings")
django.setup()

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

channel_layer = get_channel_layer()

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    async_to_sync(channel_layer.group_send)(
        "sensores",
        {
            "type": "sensor_update",  # coincide con el método en SensorConsumer
            "data": data
        }
    )
    print("📡 Datos enviados al dashboard:", data)

client = mqtt.Client()
client.connect("localhost", 1883)
client.subscribe("sensores/flujo")
client.on_message = on_message
client.loop_forever()
