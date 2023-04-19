import base64
import json
import requests
from uuid import uuid4

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, Filters, MessageHandler, Updater

from contrib.message import Message
from contrib.processor import BotProcessor
from contrib.utils import append_url, levenshtein_distance
from core.models import (
    AccessToken,
    ActiveChannel,
    BotDelegate,
    MailChannel,
    ProfileLink,
    User,
)
from main import Log
from main.Component import ChatPlatform


PLATFORM = "apps.telegram.component.TelegramBot"


def authenticate(func):
    def decorator(update, context):
        profile = ProfileLink.objects.filter(
            platform=PLATFORM,
            platform_user_id=str(update.effective_user.id),
        ).first()

        if profile is None:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Unlinked channel, please initiate the conversation from bigbot",
            )
            return

        return func(update, context, profile=profile)

    return decorator


class TelegramBot(ChatPlatform):
    def connect(self):
        self.updater.start_polling()

    def disconnect(self):
        self.updater.stop()

    def init(self):
        handlers = [
            CommandHandler("help", self.on_help),
            CommandHandler("start", self.on_start),
            CommandHandler("switch", self.on_channel_switch),
            CommandHandler("unlink", self.on_unlink),
            CallbackQueryHandler(self.on_callback),
            MessageHandler(Filters.text & (~Filters.command), self.on_message),
        ]
        token = self.get_variable("com.big.bot.telegram", "BOT_TOKEN")

        if token is None:
            raise Exception("Bot token is missing")

        updater = Updater(token=token, use_context=True)
        for handler in handlers:
            updater.dispatcher.add_handler(handler)

        self.updater = updater

    @authenticate
    def on_callback(self, update, context, *, profile):
        query = update.callback_query
        query.answer()

        data = json.loads(query.data)

        if data["type"] == "channel":
            channel = MailChannel.objects.get(id=data["id"])
            ActiveChannel.set_channel(profile.user_id, channel)
            query.edit_message_text(text=f"Channel changed to {str(channel)}")
        else:
            query.edit_message_text(text="Invalid Query")

    @authenticate
    def on_channel_switch(self, update, context, *, profile):
        channels = MailChannel.get_channels(profile.user_id)
        result = []
        for channel in channels:
            result.append(
                [
                    InlineKeyboardButton(
                        str(channel), callback_data=json.dumps({"type": "channel", "id": channel.id})
                    )
                ]
            )
        reply = InlineKeyboardMarkup(result)
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Choose an option", reply_markup=reply
        )

    @authenticate
    def on_help(self, update, context, *, profile):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=""
            "/help      Print this message.\n"
            "/switch    Change bigbot channel\n"
            "/unlink    Remove link between telegram and bigbot.\n",
        )

    @authenticate
    def on_message(self, update, context, *, profile):
        token = AccessToken.objects.get_or_create(user_id=profile.user_id)
        message = Message(body=update.message.text, contexts=[0], values=[update.message.text])
        processor = BotProcessor(profile.user_id)
        processor.process(message)


    def on_start(self, update, context):
        params = update.message.text.split(" ")
        if len(params) != 2:
            context.bot.send_message(
                chat_id=update.effective_chat.id, text="Invalid payload, please try again"
            )
            return

        payload = params[1]

        try:
            payload_data = json.loads(base64.b64decode(payload.encode()).decode())
            user_id = payload_data["user"]
            user = User.objects.get(id=user_id)
        except Exception as e:
            Log.error("TelegramBot.on_start", e)
            context.bot.send_message(
                chat_id=update.effective_chat.id, text="Invalid payload, please try again"
            )
            return

        profile = ProfileLink.objects.filter(
            platform=PLATFORM, platform_user_id=str(update.effective_user.id), user_id=user
        ).first()

        if profile is None:
            profile = ProfileLink.objects.create(
                platform=PLATFORM,
                platform_user_id=str(update.effective_user.id),
                user_id=user,
            )

        context.bot.send_message(chat_id=update.effective_chat.id, text="Bridge created successfully")

    @authenticate
    def on_unlink(self, update, context, *, profile):
        profile.delete()
        context.bot.send_message(chat_id=update.effective_chat.id, text="Bridge removed")

    def on_message_to_platform(self, profile, message):
        self.updater.dispatcher.bot.send_message(
            chat_id=int(profile.platform_user_id), text=message
        )
