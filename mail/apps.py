from django.apps import AppConfig


class MailAppConfig(AppConfig):
    name = 'mail'

    def ready(self):
        import mail.signals




