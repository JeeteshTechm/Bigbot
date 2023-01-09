from django.urls import path
from . import views

urlpatterns = [
    path('',views.dashboard_view),
    path('login/',views.login_view),
    path('logout/',views.logout_view),
    path('dashboard/',views.dashboard_view),
    path('documentation/',views.documentation_view),
    path('credential-view/',views.credential_view),
    path('skill-store/',views.skill_store),

    path('corpora-visual/',views.blank_view),
    path('skill-builder/',views.blank_view),
    path('forum/',views.blank_view),
    path('enterprise-support/',views.blank_view),
    path('hire-developer/',views.blank_view),
    path('feature-request/',views.blank_view),


    path('drop/',views.drop_corpus_view),
    path('list-trainer/',views.list_trainer_view),
    path('import_skill/',views.import_skill),
    path('settings/',views.settings_view),

    path('server/info',views.server_info),

    path('invoices/',views.invoice_view),
    path('console/project/<str:model>/',views.tree_view),
    path('console/project/<str:model>/<int:id>/',views.form_view),
    path('console/project/<str:model>/create',views.form_view),

    path('console/stack/<str:model>/',views.console_tree_view),
    path('console/stack/<str:model>/<int:id>/',views.console_from_view),
    path('console/stack/<str:model>/create',views.console_from_view),


    path('console/settings/',views.admin_config_view),

    #delete it
    path('mail/',views.mail_test),

]