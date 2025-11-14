# watermilimiter/sensores/consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class SensorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            print("Cliente WebSocket no autenticado. Conexión rechazada.")
            return
 
        self.group_name = f"sensores_{self.user.id}"
        print(f"Usuario {self.user.username} conectándose al grupo {self.group_name}")
 
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        print(f"Cliente {self.user.username} conectado al WebSocket.")


    async def disconnect(self, close_code):
   
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            print(f"Cliente {self.user.username} desconectado del grupo {self.group_name}")


    async def sensor_update(self, event):
 
        await self.send(text_data=json.dumps(event["data"]))