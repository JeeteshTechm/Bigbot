from contrib.application import AppConfig
from apps.bigbot.component import TerminalBlock
from apps.bigbot.component import PromptText,PromptURLImage
from apps.bigbot.component import InputText,InputDate,InputDateTime,InputSearchable,InputDuration,InputSelection

class Application(AppConfig):

    def init(self, source):
        return super().init(source)

    def registry(self):
        self.register(TerminalBlock(self.source))
        self.register(PromptText(self.source))
        self.register(PromptURLImage(self.source))
        self.register(InputText(self.source))
        self.register(InputDate(self.source))
        self.register(InputDateTime(self.source))
        self.register(InputSearchable(self.source))
        self.register(InputDuration(self.source))
        self.register(InputSelection(self.source))
