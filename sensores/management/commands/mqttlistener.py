import json
import paho.mqtt.client as mqtt
import os
import django
import datetime 
from django.utils import timezone 
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "watermilimiter.settings")
django.setup()
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from sensores.models import Dispositivo, LecturaSensor
from reportes.models import Alerta
from gestorUser.models import Usuario 

channel_layer = get_channel_layer()

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        print(f"Mensaje MQTT recibido: {data}")

        device_id_mqtt = data.get("sensor_id")
        flow_value = data.get("flujo")

        if not device_id_mqtt or flow_value is None:
            print(f"Error: JSON incompleto. Payload: {data}")
            return
        
        try:

            dispositivo = Dispositivo.objects.get(id_dispositivo_mqtt=device_id_mqtt)
            LecturaSensor.objects.create(
                dispositivo=dispositivo,
                valor_flujo=flow_value
            )
            print(f"Lectura guardada para {device_id_mqtt}")

            if dispositivo.limite_flujo_excesivo and flow_value > dispositivo.limite_flujo_excesivo:
                alerta_reciente = Alerta.objects.filter(
                    dispositivo=dispositivo,
                    tipo='EXCESO',
                    timestamp__gte=timezone.now() - datetime.timedelta(minutes=30)
                ).exists()
                if not alerta_reciente:
                    Alerta.objects.create(
                        usuario=dispositivo.usuario,
                        dispositivo=dispositivo,
                        tipo='EXCESO',
                        mensaje=f"¡Alerta de Flujo Excesivo! Detectado {flow_value} L/min en {dispositivo.nombre}."
                    )
                    print(f"!!! ALERTA DE EXCESO CREADA para {dispositivo.nombre} !!!")
            
            perfil_cliente = dispositivo.usuario
            cliente_user_id = perfil_cliente.usuario.id 
            cliente_group_name = f"sensores_{cliente_user_id}"

            async_to_sync(channel_layer.group_send)(
                cliente_group_name,
                {"type": "sensor_update", "data": data}
            )
            print(f"Datos enviados al CLIENTE (Grupo: {cliente_group_name})")
            
            if perfil_cliente.organizacion_admin:
                organizacion_id = perfil_cliente.organizacion_admin.id
                organizacion_group_name = f"sensores_org_{organizacion_id}"

                async_to_sync(channel_layer.group_send)(
                    organizacion_group_name,
                    {"type": "sensor_update", "data": data}
                )
                print(f"Datos enviados a la ORGANIZACIÓN (Grupo: {organizacion_group_name})")
            

        except Dispositivo.DoesNotExist:
            print(f"Error: Dispositivo con ID '{device_id_mqtt}' no encontrado en la DB.")
            return 
        except Exception as e:
            print(f"Error al guardar en DB o enviar a Channels: {e}")

    except json.JSONDecodeError:
        print(f"Error: No se pudo decodificar el mensaje MQTT: {msg.payload}")
    except Exception as e:
        print(f"Error inesperado en on_message: {e}")


client = mqtt.Client()
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mosquitto")  
print(f"Conectando a broker MQTT en: {MQTT_BROKER_HOST}")
client.connect(MQTT_BROKER_HOST, 1883)  #Cambiar a "mosquitto" para Docker y para desarrollo y probar el pub.py colocar "localhost"
client.subscribe("sensores/flujo")
client.on_message = on_message
client.loop_forever()

