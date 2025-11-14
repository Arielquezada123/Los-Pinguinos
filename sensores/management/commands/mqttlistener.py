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
            
            # 2. Guardar la lectura
            LecturaSensor.objects.create(
                dispositivo=dispositivo,
                valor_flujo=flow_value
            )
            print(f"Lectura guardada para {device_id_mqtt}")

            # 3. Obtener el perfil del CLIENTE (dueño)
            perfil_cliente = dispositivo.usuario
            cliente_user_id = perfil_cliente.usuario.id 
            
            # 4. Definir el grupo del CLIENTE
            cliente_group_name = f"sensores_{cliente_user_id}"

            # 5. Enviar al CLIENTE (como antes)
            async_to_sync(channel_layer.group_send)(
                cliente_group_name,
                {"type": "sensor_update", "data": data}
            )
            print(f"Datos enviados al CLIENTE (Grupo: {cliente_group_name})")
            

            # Comprobar si este cliente es administrado por una EMPRESA
            if perfil_cliente.empresa_asociada:
                # Obtener el ID de la EMPRESA
                empresa_user_id = perfil_cliente.empresa_asociada.usuario.id
                empresa_group_name = f"sensores_{empresa_user_id}"

                # Enviar también a la EMPRESA
                async_to_sync(channel_layer.group_send)(
                    empresa_group_name,
                    {"type": "sensor_update", "data": data}
                )
                print(f"Datos enviados a la EMPRESA (Grupo: {empresa_group_name})")
            

        except Dispositivo.DoesNotExist:
            print(f"Error: Dispositivo con ID '{device_id_mqtt}' no encontrado en la DB. No se guardó ni envió.")
            return 
        except Exception as e:
            print(f"Error al guardar en DB o enviar a Channels: {e}")

    except json.JSONDecodeError:
        print(f"Error: No se pudo decodificar el mensaje MQTT: {msg.payload}")
    except Exception as e:
        print(f"Error inesperado en on_message: {e}")


client = mqtt.Client()
client.connect("localhost", 1883) # Cambiar a "mosquitto" para Docker y para desarrollo y probar el pub.py colocar "localhost" 
client.subscribe("sensores/flujo")
client.on_message = on_message
client.loop_forever()