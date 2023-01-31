from apps.odoo.component import OdooOAuthProvider, OdooSkillProvider
from main.Config import AppConfig


class Application(AppConfig):
    def init(self, source):
        return super().init(source)

    def registry(self):
        self.register(OdooOAuthProvider)
        self.register(OdooSkillProvider)
        self.register_variable("com.big.bot.odoo", "CLIENT_ID", "Client ID")
        self.register_variable("com.big.bot.odoo", "CLIENT_SECRET", "Client Secret")
        self.register_variable(
            "com.big.bot.odoo",
            "DATA_ENDPOINT",
            "Integration endpoint URL",
            value="https://bigitsystems.com/bb/controller",
        )
        self.register_variable(
            "com.big.bot.odoo",
            "TOKEN_URL",
            "Authentication URL",
            value="https://bigitsystems.com/oauth2/auth",
        )
