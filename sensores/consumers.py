from channels.generic.websocket import AsyncWebsocketConsumer
import json

class SensorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Agregamos este socket al grupo "sensores"
        await self.channel_layer.group_add("sensores", self.channel_name)
        await self.accept()
        print("🟢 Cliente conectado al WebSocket")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("sensores", self.channel_name)
        print("🔴 Cliente desconectado")

    # Este método será llamado por channel_layer.group_send
    async def sensor_update(self, event):
        await self.send(text_data=json.dumps(event["data"]))
