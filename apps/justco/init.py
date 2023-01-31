from main.Config import AppConfig
from apps.justco.component import JustCOAdapter

class Application(AppConfig):

    def init(self, source):
        return super().init(source)

    def registry(self):
        self.register(JustCOAdapter)
