import uuid
from django.db.models.signals import post_save, pre_save

def pre_save_mail_service(sender, instance, **kwargs):
    pass

def post_save_mail_service(sender, instance, created, **kwargs):
    pass