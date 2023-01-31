from main.Config import AppConfig
from apps.myinfo.component import MyinfoOAuthProvider,MyInfo,MyInfoPost,MyInfoShare,MyInfoProperty,MyInfoPropertyOAuthProvider

class Application(AppConfig):

    def init(self, source):
        return super().init(source)

    def registry(self):
        # self.register(MyinfoOAuthProvider)
        # self.register(MyInfo)
        # self.register(MyInfoPost)
        # self.register(MyInfoShare)
        # self.register(MyInfoPropertyOAuthProvider)
        # self.register(MyInfoProperty)

        # self.register_variable("com.big.bot.myinfo", "CLIENT_ID", "MyInfo Client ID")
        # self.register_variable("com.big.bot.myinfo", "CLIENT_SECRET", "MyInfo Client SECRET")
        pass
