from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async
from gestorUser.models import Membresia, Usuario


class SensorConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]

        # 1. Rechazar usuarios no autenticados
        if not self.user.is_authenticated:
            await self.close()
            print("Cliente WebSocket no autenticado. Conexión rechazada.")
            return
        try:
            self.perfil_usuario = await database_sync_to_async(
                lambda: self.user.usuario
            )()
        except Usuario.DoesNotExist:
            self.perfil_usuario = await database_sync_to_async(
                Usuario.objects.create
            )(usuario=self.user)
        self.membresia = await database_sync_to_async(
            Membresia.objects.filter(usuario=self.perfil_usuario).first
        )()

        if self.membresia:
            org_id = self.membresia.organizacion_id
            self.group_name = f"sensores_org_{org_id}"
            print(f"Empleado {self.user.username} (Org {org_id}) conectándose al grupo {self.group_name}")
        
        else:
            self.group_name = f"sensores_{self.user.id}"
            print(f"Cliente {self.user.username} conectándose al grupo {self.group_name}")
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