from main.Config import AppConfig
from apps.telegram.component import TelegramBot


class Application(AppConfig):
    def init(self, source):
        return super().init(source)

    def registry(self):
        self.register(TelegramBot)
        self.register_variable("com.big.bot.telegram", "API_ID", "Your Telegram API ID")
        self.register_variable("com.big.bot.telegram", "API_HASH", "Your Telegram API HASH")
        self.register_variable("com.big.bot.telegram", "BOT_USERNAME", "Your Telegram Bot Username")
        self.register_variable("com.big.bot.telegram", "BOT_TOKEN", "Your Telegram Bot Token")
        self.register_variable(
            "com.big.bot.telegram", "SESSION", "Session string generated from API ID and API HASH"
        )
