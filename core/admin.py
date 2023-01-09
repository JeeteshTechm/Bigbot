import json

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html

from .models import KeycloakRealm, KeycloakUser, KeycloakUserManager, Project, Stack


@admin.register(KeycloakRealm)
class KeycloakRealmAdmin(admin.ModelAdmin):
    change_form_template = "admin/keycloak-realm.html"

    def response_change(self, request, instance):
        if "_sync_realm" in request.POST:
            instance.sync()
            return HttpResponseRedirect(
                reverse(
                    f"admin:{instance._meta.app_label}_{instance._meta.model_name}_change",
                    args=[instance.id],
                )
            )
        return super().response_change(request, instance)


@admin.register(KeycloakUser)
class KeycloakUserAdmin(admin.ModelAdmin):
    readonly_fields = ["realm", "uuid"]


@admin.register(KeycloakUserManager)
class KeycloakUserManager(admin.ModelAdmin):
    readonly_fields = ["users"]

    def users(self, instance):
        users = KeycloakUser.objects.filter(manager=instance)
        if users:
            html = format_html("<table>")
            for user in users:
                html += format_html(
                    '<tr><td><a href="{}">{}</a></td></tr>',
                    reverse(
                        f"admin:{user._meta.app_label}_{user._meta.model_name}_change",
                        args=[user.id],
                    ),
                    str(user),
                )
            html += format_html("</table>")
            print(html)
            return html
        return None


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    readonly_fields = [
        "status",
        "stack",
    ]

    def stack(self, instance):
        stack = instance.stack.first()
        if stack is None:
            return "None"
        return format_html(
            "<a href='{}'>{}</a>",
            reverse(
                f"admin:{stack._meta.app_label}_{stack._meta.model_name}_change", args=[stack.id]
            ),
            str(stack),
        )


@admin.register(Stack)
class StackAdmin(admin.ModelAdmin):
    change_form_template = "admin/stack.html"
    exclude = ["data", "project"]
    readonly_fields = [
        "project_link",
        "status",
        "step",
        "data_table",
    ]

    def data_table(self, instance):
        result = "<table><thead><tr><th>Field</th><th>Value</th></tr></thead>"
        data = json.loads(instance.data)
        for key, value in data.items():
            result += f"<tr><td>{key}</td><td>{value}</td></tr>"
        result += "</table>"
        return format_html(result)

    data_table.short_description = "Data"

    def project_link(self, instance):
        if instance.project is None:
            return "None"
        project = instance.project
        return format_html(
            "<a href='{}'>{}</a>",
            reverse(
                f"admin:{project._meta.app_label}_{project._meta.model_name}_change",
                args=[project.id],
            ),
            str(project),
        )

    project_link.short_description = "Project"

    def response_change(self, request, instance):
        if "_cancel_stack" in request.POST:
            instance.cancel()
            return HttpResponseRedirect(
                reverse(
                    f"admin:{instance._meta.app_label}_{instance._meta.model_name}_change",
                    args=[instance.id],
                )
            )
        if "_rerun_step" in request.POST:
            step = int(request.POST.get("step"))
            instance.error_message = ""
            Stack.rerun(instance, step)
            return HttpResponseRedirect(
                reverse(
                    f"admin:{instance._meta.app_label}_{instance._meta.model_name}_change",
                    args=[instance.id],
                )
            )
        if "_resume_stack" in request.POST:
            Stack.resume(instance)
            return HttpResponseRedirect(
                reverse(
                    f"admin:{instance._meta.app_label}_{instance._meta.model_name}_change",
                    args=[instance.id],
                )
            )
        return super().response_change(request, instance)
