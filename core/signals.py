from contrib.keycloak import MasterRealmController
from core.models import KeycloakRealm
from django.db.models.signals import post_delete


def on_realm_deleted(sender, instance, *args, **kwargs):
    mc = MasterRealmController()
    mc.delete_realm(instance.realm)


post_delete.connect(on_realm_deleted, sender=KeycloakController)
