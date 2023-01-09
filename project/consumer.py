import asyncio
import json
from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async, async_to_sync
from django.db.models.signals import post_save, pre_save
from django.core.signals import request_finished
from django.dispatch import receiver
import django.dispatch
from urllib.parse import parse_qs


class WebSocketConsumer(AsyncConsumer):

    def send_data(self, data):
        async_to_sync(self.send)({
            'type':'websocket.send',
            'text':json.dumps(data),
        })

    async def websocket_connect(self,event):
        params = parse_qs(self.scope['query_string'].decode('utf8'))
        uuid = params['uuid'][0]
        token = params['token'][0]
        self.user = await self.authenticate(uuid,token)
        if self.user:
            await self.send({'type':'websocket.accept', })
        pass

    async def websocket_receive(self, object):
        pass

    async def websocket_disconnect(self,event):
        pass

    @database_sync_to_async
    def authenticate(self, uuid, token):
        return False

class WebSocketDebug(AsyncConsumer):
    async def websocket_connect(self, event):
        # params = parse_qs(self.scope['query_string'].decode('utf8'))
        # uuid = params['uuid'][0]
        # token = params['token'][0]
        await self.send(
            {
                "type": "websocket.accept",
            }
        )
        await self.send({"type": "websocket.send", "text": "You are connected!"})
        pass

    async def websocket_receive(self, object):
        await self.send({"type": "websocket.send", "text": "Hello ! from backend!"})

    async def websocket_disconnect(self, event):
        pass
