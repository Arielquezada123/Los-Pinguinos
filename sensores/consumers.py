# interfaz/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class SensorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print("🟢 Cliente conectado al WebSocket")

    async def disconnect(self, close_code):
        print("🔴 Cliente desconectado")

    async def receive(self, text_data):
        data = json.loads(text_data)
        print("📡 Datos recibidos del cliente:", data)
        # reenviamos los datos al cliente para mostrarlos
        await self.send(text_data=json.dumps({
            "nivel": data.get("nivel"),
            "humedad": data.get("humedad"),
        }))
