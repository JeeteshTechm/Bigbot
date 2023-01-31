from apps.wordpress.component import SearchMeta, SearchPost, SearchTaxonomy
from main.Config import AppConfig


class Application(AppConfig):
    def init(self, source):
        return super().init(source)

    def registry(self):
        self.register(SearchMeta)
        self.register(SearchPost)
        self.register(SearchTaxonomy)
        self.register_variable(
            "com.big.bot.wordpress",
            "WORDPRESS_SERVER",
            "URL of the wordpress server",
            value="http://directory.abigbot.com/",
        )
