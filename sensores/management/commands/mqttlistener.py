# watermilimiter/sensores/management/commands/mqttlistener.py
import json
import paho.mqtt.client as mqtt
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "watermilimiter.settings")
django.setup()

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from sensores.models import Dispositivo, LecturaSensor

channel_layer = get_channel_layer()

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        print(f"Mensaje MQTT recibido: {data}")

        device_id_mqtt = data.get("sensor_id")
        flow_value = data.get("flujo")

        if not device_id_mqtt or flow_value is None:
            print(f"Error: JSON incompleto. Faltan 'sensor_id' o 'flujo'. Payload: {data}")
            return

        try:
            # 1. Buscar el dispositivo
            dispositivo = Dispositivo.objects.get(id_dispositivo_mqtt=device_id_mqtt)
            
            # 2. Guardar la lectura (como antes)
            LecturaSensor.objects.create(
                dispositivo=dispositivo,
                valor_flujo=flow_value
            )
            print(f"Lectura guardada para {device_id_mqtt}")

            # --- INICIO DE LA MODIFICACIÓN ---

            # 3. Obtener el ID del usuario dueño de este dispositivo
            # (dispositivo.usuario es un 'Usuario', dispositivo.usuario.usuario es un 'User')
            user_id = dispositivo.usuario.usuario.id 
            
            # 4. Definir el nombre del grupo privado de ESE usuario
            user_group_name = f"sensores_{user_id}"

            # 5. Enviar el mensaje SÓLO a ese grupo privado
            async_to_sync(channel_layer.group_send)(
                user_group_name,  # <-- El grupo dinámico y privado
                {
                    "type": "sensor_update",
                    "data": data
                }
            )
            print(f"Datos enviados al dashboard (Grupo: {user_group_name}): {data}")
            

        except Dispositivo.DoesNotExist:
            print(f"Error: Dispositivo con ID '{device_id_mqtt}' no encontrado en la DB. No se guardó ni envió.")
            # Si el dispositivo no existe, no podemos saber a qué grupo enviar, así que paramos.
            return 
        except Exception as e:
            print(f"Error al guardar en DB o enviar a Channels: {e}")

    except json.JSONDecodeError:
        print(f"Error: No se pudo decodificar el mensaje MQTT: {msg.payload}")
    except Exception as e:
        print(f"Error inesperado en on_message: {e}")


client = mqtt.Client()
client.connect("192.168.1.7", 1883) # Cambiar a "mosquitto" para Docker y para desarrollo y probar el pub.py colocar "localhost" 
client.subscribe("sensores/flujo")
client.on_message = on_message
client.loop_forever()