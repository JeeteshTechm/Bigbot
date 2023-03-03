import asyncio
import json
from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from urllib.parse import parse_qs

class WebSocketConsumer(AsyncConsumer):
    async def websocket_connect(self,event):
        params = parse_qs(self.scope['query_string'].decode('utf8'))
        uuid = params['uuid'][0]
        token = params['token'][0]
        self.user = await self.authenticate(uuid,token)
        if self.user:
            await self.send({'type':'websocket.accept', })

    async def websocket_receive(self, object):
        pass

    async def websocket_disconnect(self,event):
        pass

    async def authenticate(self, uuid, token):
        return await database_sync_to_async(get_user_model().objects.filter)(
            uuid=uuid, token=token
        )

class WebSocketDebug(AsyncConsumer):
    async def websocket_connect(self, event):
        await self.send({'type': 'websocket.accept', })
        await self.send({"type": "websocket.send", "text": "You are connected!"})

    async def websocket_receive(self, object):
        await self.send({"type": "websocket.send", "text": "Hello from the backend!"})

    async def websocket_disconnect(self, event):
        pass
