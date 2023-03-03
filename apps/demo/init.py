from main.Config import AppConfig
from apps.demo.component import PayPalCheckout, StripeCheckout, JustCOAdapter

class Application(AppConfig):

    def init(self, source):
        return super().init(source)

    def registry(self):
        self.register(PayPalCheckout)
        self.register(StripeCheckout)
        self.register(JustCOAdapter)
