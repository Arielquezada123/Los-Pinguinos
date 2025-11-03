# watermilimiter/sensores/consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class SensorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 1. Obtener el usuario de la sesión
        self.user = self.scope["user"]

        # 2. Rechazar conexiones de usuarios no autenticados
        if not self.user.is_authenticated:
            await self.close()
            print("Cliente WebSocket no autenticado. Conexión rechazada.")
            return

        # 3. Crear un nombre de grupo único y privado para este usuario
        self.group_name = f"sensores_{self.user.id}"
        print(f"Usuario {self.user.username} conectándose al grupo {self.group_name}")

        # 4. Unir al usuario a su grupo privado
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        print(f"Cliente {self.user.username} conectado al WebSocket.")


    async def disconnect(self, close_code):
        # 5. Descartar del grupo privado al desconectar
        # Comprobamos si 'group_name' existe por si la conexión fue rechazada en connect()
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            print(f"Cliente {self.user.username} desconectado del grupo {self.group_name}")


    async def sensor_update(self, event):
        # Esto no cambia. Simplemente reenvía los datos que recibe.
        await self.send(text_data=json.dumps(event["data"]))