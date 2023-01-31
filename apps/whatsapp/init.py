from main.Config import AppConfig

class Application(AppConfig):
    def init(self, source):
        return super().init(source)

    def registry(self):
        self.register_variable(
            "com.big.bot.whatsapp",
            "WAWEB_HOSTNAME",
            "WhatsApp Webapp container endpoint (e.g. https://example.com) (Do not include end slash)"
        )
        self.register_variable(
            "com.big.bot.whatsapp",
            "WA_USERNAME",
            "Username of the account created to manage WhatsApp Business API client"
        )
        self.register_variable("com.big.bot.whatsapp", "WA_PASSWORD", "Password for the account")
        self.register_variable(
            "com.big.bot.whatsapp",
            "WA_BUSINESS_PHONE_NUMBER",
            "Full phone number with country code of your WhatsApp Business Account \
            (For example, if your country code is 1 and your phone number 123456 \
            this value should be 1123456)"
        )