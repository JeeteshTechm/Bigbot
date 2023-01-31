import base64
import json

import requests
# for local testing
# from urllib3.exceptions import InsecureRequestWarning
# requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

from django.contrib.auth.models import Group
from django.contrib.auth.models import User

from contrib.message import Message
from contrib.processor import BotProcessor
from contrib.statement import Statement
from core.models import ActiveChannel, OAuthTokenModel, ProfileLink

USER_PROFILE_ENDPOINT = "/v1/users"
USER_LOGIN_ENDPOINT = "/v1/users/login"
MESSAGES = "/v1/messages"

AUDIO = "audio"
DOCUMENT = "document"
IMAGE = "image"
LOCATION = "location"
SYSTEM = "system"
TEXT = "text"
VIDEO = "video"
VOICE = "voice"


class WhatsAppWebhookListener:
    def __init__(self, hostname, username, password):
        self.PLATFORM = "WhatsApp"
        self.COMPONENT_NAME = "com.big.bot.whatsapp"
        self.WAWEB_HOSTNAME = hostname
        self.USERNAME = username
        self.PASSWORD = password
        
        model_object = OAuthTokenModel.objects.filter(component_name=self.COMPONENT_NAME).first()
        token = model_object.get_data() if model_object else None
        self.TOKEN = self.validate_token(token)

    def get_token(self):
        return self.TOKEN

    def validate_token(self, token):
        """Return new token if token expires or token does not exist"""
        if token:
            url = "{}{}/{}".format(self.WAWEB_HOSTNAME, USER_PROFILE_ENDPOINT, self.USERNAME)
            headers = {"Authorization": "Bearer " + token["token"] }
            # for local testing
            # r = request.get(url, headers=headers, verify=False)
            r = request.get(url, headers=headers)
            if r.status_code == 200:
                return token
            else:
                return self.login()
        else:
            return self.login()

    def login(self):
        credentials = self.USERNAME + ":" + self.PASSWORD
        credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        url = self.WAWEB_HOSTNAME + USER_LOGIN_ENDPOINT
        # for local testing
        # r = requests.post(
        #     url,
        #     headers={
        #         "Authorization": "Basic "+ credentials,
        #         "Content-Type": "application/json"
        #     },
        #     data={},
        #     verify=False,
        # )
        r = requests.post(
            url,
            headers={
                "Authorization": "Basic "+ credentials,
                "Content-Type": "application/json"
            },
            data={},
        )
        if r.status_code == 200:
            body = json.loads(r.content.decode("utf-8"))
            token = body["users"][0]
            model_object = OAuthTokenModel.objects.create(
                component_name=self.COMPONENT_NAME,
                user_id=0,
                scope=no_scope,
                data=json.dumps(token),
            )
            model_object.save()
            return token
        else:
            # raise Exception
            pass

    def respond_to_event(self, event):
        event_obj = json.loads(event)
        message = self.parse_event(event_obj)

        profile_link = ProfileLink.objects.filter(
            platform=self.PLATFORM, platform_user_id=message["sender_id"]
        ).last()
        first_time_user = False if profile_link else True
        if first_time_user:
            payload = self.parse_user_payload(message["text"]["body"])
            profile_link = self.create_profile_link_if_not_exists(
                payload, self.PLATFORM, message["sender_id"]
            )

        values = []
        parsed_message = {}
        attachment = None
        if message["type"] == TEXT:
            parsed_message["body"] = message["text"]["body"]
        else:
            parsed_message["body"] = ""
            attachment = message[message["type"]]
        values.append(parsed_message["body"])
        parsed_message["contexts"] = [0]
        parsed_message["location"] = self.WAWEB_HOSTNAME
        parsed_message["values"] = values
        replies = self.get_replies(
            profile_link.user_id, parsed_message, message["type"], attachment
        )
        for reply_message in replies:
            data = {}
            data["to"] = message["sender_id"]
            data["type"], data[data["type"]] = self.convert_reply_to_platform_type(reply_message)

            url = "{}{}".format(self.WAWEB_HOSTNAME, MESSAGES)
            token = self.get_token()
            headers = { "Authorization": "Bearer " + token["token"] }
            # requests.post(url=url, headers=headers, json=data, verify=False)
            requests.post(url=url, headers=headers, json=data)

    def parse_event(self, obj):
        message = {}
        if obj.get("contacts"):
            message["sender_id"] = obj["contacts"][0]["wa_id"]
        if obj.get("messages"):
            message["message_id"] = obj["messages"][0]["id"]
            message["timestamp"] = obj["messages"][0]["timestamp"]
            message["type"] = obj["messages"][0]["type"]
            message[message["type"]] = obj["messages"][0][message["type"]]
        return message

    def create_profile_link_if_not_exists(self, payload, platform, sender_id):
        # Case when user is redirected from Big Bot
        user = None
        if payload:
            user_id = base64.b64decode(payload.encode("utf-8")).decode("utf-8")
            user = User.objects.filter(id=user_id).first()
        # Case when user starts the conversation directly in WhatsApp
        else:
            user = User.objects.create(first_name="WhatsApp Visitor")
            public_group = Group.objects.get(name="public")
            user.groups.add(public_group)
            user.save()
        profile_link = ProfileLink.objects.create(
            user_id=user, platform=self.PLATFORM, platform_user_id=sender_id
        )
        return profile_link

    def parse_user_payload(self, text):
        # text is in this format - "[payload] Let's continue our chat."
        bracket_start = text.find("[")
        bracket_end = text.find("]")
        if bracket_start != 0 or (bracket_start == -1 and bracket_end == -1):
            return None
        else:
            return text[bracket_start + 1: bracket_end]

    def get_replies(self, user, message, message_type, attachment):
        processor = BotProcessor(user)
        ActiveChannel.set_channel(user, processor.channel)

        if message_type == TEXT:
            msg = Message(
                body=message["body"],
                contexts=message["contexts"],
                location=message["location"],
                values=message["values"]
            )
            processor.process(msg)
            data = []
            for msg_id in processor.message_ids:
                data.append(MailMessage.objects.get(id=msg_id.id).serialize(user))
            return data

    def get_reply_type(self, message):
        """Get WhatsApp message type from reply message"""
        # To add more types
        return TEXT

    def convert_reply_to_platform_type(self, message):
        # message is MailMessage serialized form
        message_type = self.get_reply_type(message)
        data = {}
        if message_type == TEXT:
            data["body"] = message["statement"]["text"]
        return message_type, data
