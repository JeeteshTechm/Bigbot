from main.Config import AppConfig

class Application(AppConfig):
    def init(self, source):
        return super().init(source)

    def registry(self):
        pass