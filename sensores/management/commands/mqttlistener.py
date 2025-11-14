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
from reportes.models import Alerta  #
from gestorUser.models import Usuario #

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

            # --- INICIO DE LÓGICA DE ALERTA (de tu compañero) ---
            LIMITE_FLUJO_EXCESIVO = 50.0 # Define tu límite (ej. 50 L/min)

            if flow_value > LIMITE_FLUJO_EXCESIVO:
                # ¡Flujo excesivo detectado!
                
                # Evitar duplicados: revisa si ya hay una alerta reciente
                alerta_reciente = Alerta.objects.filter(
                    dispositivo=dispositivo,
                    tipo='EXCESO',
                    # Busca alertas de este tipo en los últimos 30 minutos
                    timestamp__gte=timezone.now() - datetime.timedelta(minutes=30)
                ).exists()

                if not alerta_reciente:
                    # Si no hay alertas recientes, crea una nueva
                    Alerta.objects.create(
                        usuario=dispositivo.usuario, # Asigna al perfil de Usuario
                        dispositivo=dispositivo,
                        tipo='EXCESO',
                        mensaje=f"¡Alerta de Flujo Excesivo! Detectado {flow_value} L/min en {dispositivo.nombre}."
                    )
                    print(f"!!! ALERTA DE EXCESO CREADA para {dispositivo.nombre} !!!")
            
            # --- FIN DE LÓGICA DE ALERTA ---

            
            # --- INICIO DE LÓGICA DE WEBSOCKET (Corregida y Unificada) ---
            
            # (Se eliminó el bloque de código duplicado y con error de sintaxis que estaba aquí)

            # 3. Obtener el perfil del CLIENTE (dueño)
            perfil_cliente = dispositivo.usuario
            cliente_user_id = perfil_cliente.usuario.id 
            
            # 4. Definir el grupo del CLIENTE
            cliente_group_name = f"sensores_{cliente_user_id}"

            # 5. Enviar al CLIENTE
            async_to_sync(channel_layer.group_send)(
                cliente_group_name,
                {"type": "sensor_update", "data": data}
            )
            print(f"Datos enviados al CLIENTE (Grupo: {cliente_group_name})")
            
            # 6. Comprobar si este cliente es administrado por una EMPRESA
            if perfil_cliente.empresa_asociada:
                # 7. Obtener el ID de la EMPRESA
                empresa_user_id = perfil_cliente.empresa_asociada.usuario.id
                empresa_group_name = f"sensores_{empresa_user_id}"

                # 8. Enviar también a la EMPRESA
                async_to_sync(channel_layer.group_send)(
                    empresa_group_name,
                    {"type": "sensor_update", "data": data}
                )
                print(f"Datos enviados a la EMPRESA (Grupo: {empresa_group_name})")
            
            # --- FIN DE LÓGICA DE WEBSOCKET ---

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

# (Usamos la variable de entorno o 'localhost' si estás en desarrollo local)
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost") 
print(f"Conectando a broker MQTT en: {MQTT_BROKER_HOST}")


client = mqtt.Client()
client.connect("localhost", 1883) ##Cambiar a "mosquitto" para Docker y para desarrollo y probar el pub.py colocar "localhost"
client.subscribe("sensores/flujo")
client.on_message = on_message
client.loop_forever()
