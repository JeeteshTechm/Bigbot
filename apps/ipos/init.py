from apps.ipos.component import IPOSProviders
from main.Config import AppConfig


class Application(AppConfig):
    def init(self, source):
        return super().init(source)

    def registry(self):
        # self.register_variable("ai.bigbot.ipos", "WORDPRESS_SERVER", "Wordpress Server", str)
        # self.register_variable(
        #     "ai.bigbot.ipos", "API_KEY", "Big Bot's wordpress plugin API key", str
        # )
        # self.register_variable(
        #     "ai.bigbot.ipos", "API_SECRET", "Big Bot's wordpress plugin API secret", str
        # )
        self.register_data_exchange(
            IPOSProviders,
            "IPOS Bot Providers",
            "List the bots assigned to providers in a selection node",
        )
        self.register_variable(
            "ai.bigbot.ipos",
            "BOT_GROUPS",
            "Comma separeted list of groups used to filter the bots assigned to providers (can be left blank)",
            str,
        )
