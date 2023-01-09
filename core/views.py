import json
import yaml

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django_middleware_global_request.middleware import get_request
import requests

from contrib import permissions, utils
from contrib.decorators import (
    keycloak_authenticate,
    keycloak_authenticate_get,
    keycloak_authenticate_header,
    verify_jsonrpc,
)
from contrib.exceptions import JsonRPCException
from contrib.http import JsonRPCResponse
from contrib.keycloak import KeycloakController
from contrib.manager import JsonRPC
from main import Log

from .models import Project, KeycloakRealm, KeycloakUserManager


@csrf_exempt
def _create_local_user(request):
    import os
    from django.contrib.auth.models import User

    username = os.getenv("LOCAL_USERNAME")
    password = os.getenv("LOCAL_PASSWORD")
    print("====Local Username====", username)
    if not username and password:
        return HttpResponse(status=400)
    user = User.objects.filter(username=username).first()
    if not user:
        user = User.objects.create(
            username=username,
            is_superuser=True,
            is_staff=True,
        )
        user.set_password(password)
    else:
        user.set_password(password)
    user.save()
    return HttpResponse()


@csrf_exempt
@keycloak_authenticate_header(permissions.SUPERUSER)
@verify_jsonrpc({"method": "invite"})
def _instance_invite_user(request):
    params = request.jsonrpc["params"]
    email = params.get("email")
    client_id = params.get("clientId")
    redirect_uri = params.get("redirectUri")

    error = {}
    if email is None:
        error["email"] = "Field missing"
    if client_id is None:
        error["client_id"] = "Field missing"
    if redirect_uri is None:
        error["redirect_uri"] = "Field missing"

    if error:
        return JsonRPCResponse(error=error, status=400)

    result = KeycloakUserManager.invite_user(request.keycloak_user, email, client_id, redirect_uri)
    if result:
        return JsonRPCResponse(result)
    return JsonRPCResponse("Invalid token", status=400)


@require_GET
@keycloak_authenticate_get("access_token", *permissions.USER)
def _instance_list_user(request):
    users = KeycloakUserManager.list_users(request.keycloak_user)
    if users:
        return JsonResponse(users, safe=False)
    return HttpResponse("instance_uri is not part of any project", status=400)


def _json_rpc_model_request(project, token, model, method, params=[]):
    headers = {"Authorization": f"Bearer {token}", "content-type": "application/json"}
    object = {
        "jsonrpc": "2.0",
        "method": "execute_kw",
        "id": None,
        "params": [project.api_key, project.api_secret, model, method, *params],
    }
    url = project.instance_uri + "/jsonrpc/object"
    data = json.dumps(object)
    response = requests.post(url=url, headers=headers, data=data)
    print("======response=====", response)
    if response.status_code == 200:
        return response.json()["result"]
    return False


@csrf_exempt
@require_POST
@verify_jsonrpc(
    {"method": ["authenticate", "list_instance", "logout", "profile", "signup", "switch_realm"]}
)
def console_common_v1(request, *args, **kwargs):
    """this is for origin server aka main portal"""
    method = request.jsonrpc["method"]
    params = request.jsonrpc["params"]

    if method == "authenticate":
        openid_token = KeycloakUserManager.authenticate(*params)
        if openid_token:
            data = {
                "access_uuid": "",
                "access_token": openid_token,
            }
            return JsonRPCResponse(data)
        return HttpResponse(status=401)

    elif method == "list_instance":
        token, user = KeycloakUserManager.authenticate_token(params[1])
        if not token:
            return HttpResponse(status=401)
        current = None
        projects, current = KeycloakUserManager.list_instances(token, user)
        return JsonRPCResponse({"current": current, "instances": projects})

    elif method == "logout":
        token, user = KeycloakUserManager.authenticate_token(params[0])
        data = KeycloakUserManager.logout(user, token)
        if data:
            return JsonRPCResponse(data)
        return JsonRPCResponse(error=False, status=400)

    elif method == "profile":
        token, user = KeycloakUserManager.authenticate_token(params[1])
        if not user:
            return JsonRPCResponse(error="Unauthorized", status=401)
        return JsonRPCResponse(user)

    elif method == "signup":
        openid_token = params[1]
        token, user = KeycloakUserManager.authenticate_token(openid_token)
        data = True
        return JsonResponse({"jsonrpc": "2.0", "result": data, "id": None})

    elif method == "switch_realm":
        token, user = KeycloakUserManager.authenticate_token(params[1])
        if not token:
            return JsonRPCResponse(error="Unauthorized", status=401)
        token = KeycloakUserManager.switch_realm(user, params[2])
        if not token:
            return JsonRPCResponse(error="Unauthorized", status=401)
        return JsonRPCResponse({"access_uuid": "", "access_token": token})


@csrf_exempt
@keycloak_authenticate_get("token")
def console_skill_draft(request, *args, **kwargs):
    from core.models import SkillStore

    if request.method == "GET":
        return JsonResponse([], safe=False)
    elif request.method == "POST":
        body = utils.get_body(request)
        record = SkillStore.objects.create(
            name=body["name"],
        )
        return HttpResponse(str(record.id))
    elif request.method == "PUT":
        id = utils.get_int(request, "id")
        body = utils.get_body(request)
        record = SkillStore.objects.get(id=id)
        record.name = body["name"]
        record.save()
        return HttpResponse("OK", status=200)
    elif request.method == "DELETE":
        id = utils.get_int(request, "id")
        record = SkillStore.objects.get(id=id)
        record.delete()
        return HttpResponse("OK", status=200)
    return HttpResponse(status=405)


@csrf_exempt
@require_POST
@keycloak_authenticate_header(permissions.SUPERUSER)
@verify_jsonrpc({"method": "execute_kw"}, 4)
def console_object_v1(request):
    """this is for origin server aka main portal"""
    id = request.jsonrpc["id"]
    method = request.jsonrpc["method"]
    params = request.jsonrpc["params"]

    model = params[0]
    model_method = params[1]

    result = JsonRPC(request.keycloak_user).execute_kw(model, model_method, params[2:], id)
    return JsonRPCResponse(result)


@csrf_exempt
@require_POST
@verify_jsonrpc({"method": "execute_kw"}, 4)
def generic_object(request, *args, **kwargs):
    # TODO (cuauh): Keycloak permissions
    id = request.jsonrpc["id"]
    method = request.jsonrpc["method"]
    params = request.jsonrpc["params"]

    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    if not request.user.is_superuser:
        return HttpResponse(status=403)

    model = params[2]
    model_method = params[3]

    result = JsonRPC(request.keycloak_user).execute_kw(model, model_method, params[4:], id)
    return JsonRPCResponse(result)


@csrf_exempt
@require_POST
@keycloak_authenticate_get("access_token")
def instance_corpus_v3(request, *args, **kwargs):
    project = KeycloakUserManager.get_user_project(request.keycloak_user)
    if project:
        file = request.FILES["file"]
        filename = file.name
        if filename.endswith(".yml"):
            corpus_data = yaml.load(file)
            categories = corpus_data["categories"]
            conversations = corpus_data["conversations"]
            delegate = int(request.POST.get("delegate_id"))
            for record in conversations:
                res_1 = record[0]
                res_2 = record[1:]
                _json_rpc_model_request(
                    project,
                    request.keycloak_encoded_token,
                    "input.pattern",
                    "post_values",
                    [
                        res_1,
                        [
                            {
                                "delegate_id": delegate,
                                "responseText": response,
                                "responseType": {"value": "big.bot.core.text"},
                            }
                            for response in res_2
                        ],
                        None,
                    ],
                )
            return HttpResponse(status=200)
        pass
    return HttpResponse("Bad Request", status=400)


@require_GET
@keycloak_authenticate_get("access_token", *permissions.ADMIN)
def instance_get_user(request, user_id):
    user = KeycloakUserManager.get_user(request.keycloak_user, user_id)
    if user:
        return JsonRPCResponse(user)
    return JsonRPCResponse(error="Invalid user id", status=400)


@csrf_exempt
@keycloak_authenticate_get("access_token")
def instance_list_train(request, *args, **kwargs):
    project = KeycloakUserManager.get_user_project(request.keycloak_user)
    if project:
        if request.method == "DELETE":
            _json_rpc_model_request(project, token, "input.pattern", "delete_list_values", [])
            return HttpResponse(status=200)
        elif request.method == "POST":
            data_list = request.POST.getlist("data_list")
            if data_list:
                _json_rpc_model_request(
                    project,
                    request.keycloak_encoded_token,
                    "input.pattern",
                    "post_list_values",
                    [data_list],
                )
            return HttpResponse(status=200)
    return HttpResponse(status=400)


@csrf_exempt
@require_POST
@keycloak_authenticate_header()
@verify_jsonrpc({"method": "execute_kw"})
def instance_object_v1(request, *args, **kwargs):
    """This view pipes the requests to the customer server"""
    if "multipart/form-data" in request.META.get("CONTENT_TYPE"):
        return instance_object_multipart_v1(request, *args, **kwargs)

    method = request.jsonrpc["method"]
    params = request.jsonrpc["params"]

    model = params[0]
    method = params[1]
    parameters = params[2:]
    project = KeycloakUserManager.get_user_project(request.keycloak_user)
    if project:
        headers = {
            "Authorization": f"Bearer {request.keycloak_encoded_token}",
            "content-type": "application/json",
        }
        object = {
            "jsonrpc": "2.0",
            "method": "execute_kw",
            "id": None,
            "params": [
                project.api_key,
                project.api_secret,
                model,
                method,
                *parameters,
            ],
        }
        url = project.instance_uri + "/jsonrpc/1/instance/object"
        data = json.dumps(object)
        response = requests.post(url=url, headers=headers, data=data)

        if response.status_code == 200:
            refreshed_token = response.headers.get("Access-Token")
            new_response = JsonResponse(response.json())
            if refreshed_token:
                new_response["Access-Token"] = refreshed_token
            return new_response
        return HttpResponse(response.content, status=response.status_code)
    return HttpResponse(status=400)


@csrf_exempt
@require_POST
@verify_jsonrpc({"method": "execute_kw"})
def instance_object_multipart_v1(request, *args, **kwargs):
    """ """
    import re

    print("===== Multipart =====")

    jsonrpc_version = request.POST.get("jsonrpc")
    method = request.POST.get("method")
    params = request.POST.get("params", "[]")
    params = re.sub(r'\\"', '"', params)
    params = json.loads(params)
    id = request.POST.get("id")
    files = request.FILES.getlist("files")
    files = [("files", f.file.getvalue()) for f in files]

    openid_token = params[2]
    token = KeycloakUserManager.authenticate_token(openid_token)

    if not token:
        return HttpResponse("Unauthorized", status=401)

    model = params[3]
    method = params[4]
    parameters = params[5:]
    project = KeycloakUserManager.get_user_project(token)

    if project:
        data = {
            "jsonrpc": "2.0",
            "method": "execute_kw",
            "id": None,
            "params": json.dumps(
                [
                    project.api_key,
                    project.api_secret,
                    model,
                    method,
                    *parameters,
                ],
                separators=(",", ":"),
            ),
        }
        url = project.instance_uri + "/jsonrpc/1/instance/object"
        response = requests.post(url, data=data, files=files)

        if response.status_code == 200:
            return JsonResponse(response.json())
        return HttpResponse(response.content, status=response.status_code)

    return HttpResponse("instance_uri is not part of any project", status=400)


@csrf_exempt
@keycloak_authenticate_header()
@verify_jsonrpc({"method": ["post_values", "read"]})
def instance_settings_v3(request, *args, **kwargs):
    method = request.jsonrpc["method"]
    params = request.jsonrpc["params"]
    project = KeycloakUserManager.get_user_project(request.keycloak_user)
    if project:
        token = request.keycloak_encoded_token
        if method == "post_values":
            response = requests.post(
                f"{project.instance_uri}/jsonrpc/object",
                json={
                    "id": None,
                    "jsonrpc": "2.0",
                    "method": "execute_kw",
                    "params": [
                        project.api_key,
                        project.api_secret,
                        "preference",
                        "post_bundle_values",
                        params,
                    ],
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            return HttpResponse(
                response.text,
                content_type=response.headers["Content-Type"],
                status=response.status_code,
            )
        elif method == "read":
            pref = _json_rpc_model_request(
                project,
                token,
                "preference",
                "get_bundle_values",
                [project.api_key, project.api_secret],
            )
            return JsonRPCResponse(pref)

    return JsonRPCResponse(error="Invalid request", status=400)


@csrf_exempt
@require_POST
@keycloak_authenticate("superuser")
@verify_jsonrpc()
def instance_realm(request):
    """Create, delete, and manage a customer project"""
    # TODO (cuauh): remove if safe
    body = utils.get_body(request)

    params = body["params"]
    access_token = params[0]

    method = body["method"]
    callback = getattr(KeycloakRealm, method, None)

    if callback is None:
        return HttpResponse(f"Invalid method: {method}", status=400)

    callback(*params[1:])
    return HttpResponse()


@csrf_exempt
@require_POST
@keycloak_authenticate_header()
@verify_jsonrpc({"method": ["import", "export"]})
def instance_skill(request):
    method = request.jsonrpc["method"]
    params = request.jsonrpc["params"]

    project = KeycloakUserManager.get_user_project(request.keycloak_user)

    if method == "export" and project:
        record = _json_rpc_model_request(
            project,
            request.keycloak_encoded_token,
            "delegate.skill",
            "read",
            [params[0], {"fields": ["data", "package"]}],
        )
        response = JsonRPCResponse(record["data"])
        response["Content-Disposition"] = f"attachment; filename={record['package']}.json"
        return response

    if method == "import" and project:
        Log.debug("instance_skill", params)
        return HttpResponse("", status=400)

    return JsonRPCResponse(error="Indalid request", status=400)


@csrf_exempt
@require_POST
@keycloak_authenticate_header(*permissions.ADMIN)
@verify_jsonrpc({"method": ["detail", "invite", "list", "update_credentials"]})
def instance_users(request):
    method = request.jsonrpc["method"]
    params = request.jsonrpc["params"]

    if method == "detail":
        project = KeycloakUserManager.get_user_project(request.keycloak_user)
        result = None

        if project:
            result = _json_rpc_model_request(
                project,
                request.keycloak_encoded_token,
                "keycloak.user",
                "get_user",
                [params.get("id")],
            )

        if result:
            return JsonRPCResponse(result)
        return JsonRPCResponse(error="Invalid request", status=400)

    elif method == "invite":
        client_id = params.get("clientId")
        email = params.get("email")
        redirect_uri = params.get("redirectUri")

        error = {}
        if email is None:
            error["email"] = "Field missing"
        if client_id is None:
            error["client_id"] = "Field missing"
        if redirect_uri is None:
            error["redirect_uri"] = "Field missing"

        if error:
            return JsonRPCResponse(error=error, status=400)

        result = KeycloakUserManager.invite_user(
            request.keycloak_user, email, client_id, redirect_uri
        )
        if result:
            return JsonRPCResponse(result)

    elif method == "list":
        users = KeycloakUserManager.list_users(request.keycloak_user)
        if users:
            return JsonRPCResponse(users)

    elif method == "update_credentials":
        project = KeycloakUserManager.get_user_project(request.keycloak_user)
        result = None

        if project:
            result = _json_rpc_model_request(
                project, request.keycloak_encoded_token, "keycloak.user", "update", [params]
            )

        if result:
            return JsonRPCResponse(result)

    return JsonRPCResponse(error="Invalid request", status=400)


@csrf_exempt
@keycloak_authenticate_header()
def kc_get_clients(request):
    """Returns a list of available clients"""

    def get_full_url(uri):
        from django.conf import settings

        res = settings.KEYCLOAK_CONFIG["KEYCLOAK_SERVER_URL"]
        if res[-1:] == uri[0] and uri[0] == "/":
            res = res + uri[1:]
        else:
            res += uri
        if res[-1:] == "*":
            res = res[:-1]
        return res

    realm = KeycloakRealm.objects.filter(realm=request.keycloak_token["rlm"]).first()
    if realm is None:
        return JsonRPCResponse(error="Indalid realm", status="400")

    clients = realm.get_clients()
    clients = list(
        filter(
            lambda c: len(c.get("baseUrl", "")) > 0,
            filter(lambda c: len(c.get("redirectUris", [])) > 0, clients),
        )
    )

    clients = [
        {
            "clientId": c["clientId"],
            "name": c.get("name", ""),
            "redirectUris": [
                uri if uri[:4] == "http" else get_full_url(uri) for uri in c["redirectUris"]
            ],
        }
        for c in clients
    ]

    return JsonRPCResponse(clients)


@csrf_exempt
@keycloak_authenticate_header()
@verify_jsonrpc()
def registry(request):
    """This method pipes requests to the registry view of the customer server"""
    project = KeycloakUserManager.get_user_project(request.keycloak_user)
    if not project:
        return JsonRPCResponse(error="Invalid user", status=400)

    response = requests.post(
        utils.append_url(project.instance_uri, "/jsonrpc/registry"),
        json=request.jsonrpc,
        headers={"Authorization": f"Bearer {request.keycloak_encoded_token}"},
    )

    try:
        response.raise_for_status()
    except:
        return HttpResponse(
            response.content,
            content_type=response.headers["content-type"],
            status=response.status_code,
        )

    return JsonResponse(response.json())


@csrf_exempt
def skill_builder_blocks(request, *args, **kwargs):
    """Returns the list of all available blocks for the skill builder"""
    from main import Binder

    return JsonRPCResponse(Binder.get_blocks())


@csrf_exempt
def skill_builder_connections(request, *args, **kwargs):
    """Returns a list of possible connections for a particular block.

    Args:
        component (str): The name of the block including its module, e.g. "main.Block.PropmtText"
        properties (list): List of the block properties, a property has the structure:
            {"name" "<porperty_name>", "value": <object>}. Every block uses custom properties

    Returns:
        list: A list of lists, every list has the structure:
        [VALUE_OF_THE_CONNECTIOM, "Human readable value"], e.g.
        [[BLOCK_MOVE, "Next"], [BLOCK_REJECT, "Reject"]]
    """
    from main import Binder

    component = request.GET.get("component")
    properties = utils.get_body(request)
    result = Binder.get_connections(component, properties)
    return JsonRPCResponse(result)


@csrf_exempt
def skill_builder_nodes(request, *args, **kwargs):
    """Returns a list of all avilable nodes"""
    from main import Node

    try:
        result = Node.all()
        return JsonRPCResponse(result)
    except Exception as e:
        Log.error("skill_buider_nodes", e)
        return JsonRPCResponse(error=e, status=500)


@csrf_exempt
def skill_builder_validate(request, *args, **kwargs):
    """Validates a skill"""
    if request.method != "POST":
        return HttpResponse(status=405)
    from main import Binder

    body = utils.get_body(request)
    if body:
        try:
            Binder.validate_skill(body)
            return JsonRPCResponse(True, status=200)
        except JsonRPCException as e:
            return JsonRPCResponse(error=e, status=406)
        except Exception as e:
            return HttpResponse(str(e), status=406)
    return HttpResponse("Body Missing.", status=406)


@csrf_exempt
def store_component(request, *args, **kwargs):
    data = []
    data.append(
        {
            "name": "Odoo OAuth Provider",
            "component": "apps.odoo.component.OdooOAuthProvider",
            "description": "This is Bigbot odoo oauth provider.",
        }
    )
    data.append(
        {
            "name": "Odoo Skill Provider",
            "component": "apps.odoo.component.OdooSkillProvider",
            "description": "This is Bigbot odoo skill provider.",
        }
    )
    return JsonResponse(data, safe=False)


@csrf_exempt
def store_package(request, *args, **kwargs):
    return HttpResponse(status=404)
