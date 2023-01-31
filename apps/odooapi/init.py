from main.Config import AppConfig
from apps.odooapi.component import OdooApiOAuthProvider, OdooApiSkillProvider


class Application(AppConfig):

    def init(self, source):
        return super().init(source)

    def registry(self):
        # self.register(OdooApiOAuthProvider)
        # self.register(OdooApiSkillProvider)
        pass
