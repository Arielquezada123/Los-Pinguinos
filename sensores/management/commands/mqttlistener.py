# watermilimiter/sensores/management/commands/mqttlistener.py
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
from reportes.models import Alerta # <--- NUEVO: Importa el modelo de Alerta

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

            # --- INICIO DE LÓGICA DE ALERTA ---
            LIMITE_FLUJO_EXCESIVO = 50.0 # Define tu límite (ej. 50 L/min)

            if flow_value > LIMITE_FLUJO_EXCESIVO:
                # ¡Flujo excesivo detectado!
                
                # Evitar duplicados: revisa si ya hay una alerta reciente para este sensor
                alerta_reciente = Alerta.objects.filter(
                    dispositivo=dispositivo,
                    tipo='EXCESO',
                    # Busca alertas de este tipo en los últimos 30 minutos
                    timestamp__gte=timezone.now() - datetime.timedelta(minutes=30)
                ).exists()

                if not alerta_reciente:
                    # Si no hay alertas recientes, crea una nueva
                    Alerta.objects.create(
                        usuario=dispositivo.usuario, # 'dispositivo.usuario' es la instancia de 'Usuario' (de gestorUser)
                        dispositivo=dispositivo,
                        tipo='EXCESO',
                        mensaje=f"¡Alerta de Flujo Excesivo! Detectado {flow_value} L/min en {dispositivo.nombre}."
                    )
                    print(f"!!! ALERTA DE EXCESO CREADA para {dispositivo.nombre} !!!")
            # --- FIN DE LÓGICA DE ALERTA ---


            # 3. Obtener el ID del usuario dueño de este dispositivo
            user_id = dispositivo.usuario.usuario.id 
            
            # 4. Definir el nombre del grupo privado de ESE usuario
            user_group_name = f"sensores_{user_id}"

            # 5. Enviar el mensaje SÓLO a ese grupo privado (esto ya lo tenías)
            async_to_sync(channel_layer.group_send)(
                user_group_name,
                {
                    "type": "sensor_update",
                    "data": data
                }
            )
            print(f"Datos enviados al dashboard (Grupo: {user_group_name}): {data}")
            

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
client.connect("localhost", 1883) ##Cambiar a "mosquitto" para Docker y para desarrollo y probar el pub.py colocar "localhost"
client.subscribe("sensores/flujo")
client.on_message = on_message
client.loop_forever()
