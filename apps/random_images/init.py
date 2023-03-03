from apps.random_images.component import GetRandomImage
from main.Config import AppConfig


class Application(AppConfig):
    def registry(self):
        self.register_data_exchange(
            GetRandomImage,
            "Random Image",
            "Get a random image",
            output=[
                {
                    "description": "URL to random image",
                    "name": "random_image",
                    "readable": "Random Image",
                    "type": "url",
                }
            ],
        )
