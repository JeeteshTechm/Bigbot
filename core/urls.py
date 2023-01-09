from django.urls import path
from . import views

urlpatterns = [
    # old
    path("jsonrpc/object", views.generic_object),
    # new
    path("jsonrpc/1/console/object", views.console_object_v1),
    path("jsonrpc/1/console/common", views.console_common_v1),
    # remote api
    path("jsonrpc/1/instance/object", views.instance_object_v1),
    # Skill builder API START
    path("api/v3/registry", views.registry),
    path("api/v3/skill/builder/blocks", views.skill_builder_blocks),
    path("api/v3/skill/builder/connections", views.skill_builder_connections),
    path("api/v3/skill/builder/nodes", views.skill_builder_nodes),
    path("api/v3/skill/builder/validate", views.skill_builder_validate),
    path("api/v3/store/package", views.store_package),
    path("api/v3/store/component", views.store_component),
    path("api/v3/console/skill/draft", views.console_skill_draft),
    # Skill builder API END
    # new point
    path("api/v3/instance/corpus", views.instance_corpus_v3),
    path("api/v3/instance/invite/user", views._instance_invite_user),
    path("api/v3/instance/list/train", views.instance_list_train),
    path("api/v3/instance/list/users", views._instance_list_user),
    path("api/v3/instance/list/users/<uuid:user_id>", views.instance_get_user),
    path("api/v3/instance/realm", views.instance_realm),
    path("api/v3/instance/settings", views.instance_settings_v3),
    path("api/v3/instance/skill", views.instance_skill),
    path("api/v3/instance/users", views.instance_users),
    path("api/v3/local/user", views._create_local_user),
    # Keycloak uitlity api
    path("api/v3/kc/clients", views.kc_get_clients),
]
