from contrib.application import AppConfig
from .component import VoiceFeatureScoreService
from .components import AsyncVoiceFeatureScoreService

class Application(AppConfig):

    def init(self, config):
        pass

    def registry(self, object):
        object.register(VoiceFeatureScoreService)
