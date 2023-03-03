from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon import functions
from telethon import events
from telethon.errors.rpcerrorlist import PhoneNumberInvalidError
# Use your own values from my.telegram.org
import json

class TelegramAPI:
    def __init__(self,session):
        self.API_ID = 3903449
        self.API_HASH = "52458e289105630a95b496256f4f333"
        self.BOT_TOKEN = bot_token
        self.session = session
    def make_connection(self):
        self.client = TelegramClient(StringSession(self.session), self.API_ID, self.API_HASH)
        self.client.connect()
        if not self.client.is_user_authorized():
            phone = input("please enter your Telegram number ")
            sent =  self.client.send_code_request(phone,force_sms=True)
            print(sent)
            self.client.sign_in(phone,input("Enter the code=  "))
            self.session = self.client.session.save()
        return {"token":self.session}

    def disconnect(self):
        if self.client:
            self.client.disconnect()
        else:
            return

    # method invalid with bot
    def chat_list(self):
        chats = self.client.iter_dialogs()
        return {
            "chat_list": [
                {
                    "name" : dialog.name,
                    "id" : dialog.id,
                } for dialog in chats
            ]
        }

    # method invalid with bot
    def get_message(self,chat_id,message_count=None):
        messages = self.client.iter_messages(chat_id,limit=message_count)
        return {
            "messages" : [
                {
                    "sender_id" : msg._sender_id,
                    "sender_username" : msg._sender.username,
                    "text" : msg.text,
                    "date" : msg.date
                } for msg in messages
            ]
        }

    # method valid with bot
    def _get_messages(self, message_ids: list):
        result = self.client(functions.messages.GetMessagesRequest(id=message_ids))
        return {
            "messages" : [
                {
                    "sender_id" : msg.from_id.user_id
                        if msg.from_id
                        else msg.peer_id.user_id,
                    "sender_username" : self.client.get_entity(msg.from_id.user_id).username
                        if msg.from_id
                        else self.client.get_entity(msg.peer_id.user_id).username,
                    "text" : msg.message,
                    "date" : msg.date,
                    "is_self": True if msg.from_id else False
                } for msg in result.messages
            ]
        }

    # method invalid with bot
    def send_message(self, chat_id,message):
        self.client.send_message(chat_id,message)
        return self.get_message(chat_id=chat_id,message_count=1)

    # method valid with bot
    def _send_message(self, chat_id,message):
        sent_message = self.client.send_message(chat_id,message)
        return {
            "message_id": sent_message.id,
            "receiver_id": sent_message.peer_id.user_id,
            "text": sent_message.message,
            "date": sent_message.date
        }

    def get_me(self):
        me = self.client.get_me()
        return me.__dict__

    def listen_updates(self):
        '''
        Method to run the client forever
        '''
        self.client = TelegramClient(StringSession(self.session), self.API_ID, self.API_HASH)
        if self.BOT_TOKEN:
            self.client.start(bot_token=self.BOT_TOKEN)
        self.handlers = [
            (self.start_handler, events.NewMessage(pattern="/start(?: \w+)")),
            (self.message_handler, events.NewMessage),
        ]
        self.register_handlers()
        with self.client:
            self.client.run_until_disconnected()

    def register_handlers(self):
        for handler, event in self.handlers:
            self.client.add_event_handler(handler, event)

    async def start_handler(self, event):
        text_chunks = event.message.raw_text.split()
        if text_chunks[1] == text_chunks[-1]:
            payload = text_chunks[1]
            print(payload)
            # TODO: send this payload to identify the sender
        message = ""
        await event.respond(message)

    async def message_handler(self, event):
        # TODO: process the incoming message and respond to it
        message = ""
        await event.respond(message)
