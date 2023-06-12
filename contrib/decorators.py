import re

import jwt

from contrib.exceptions import JsonRPCException
from contrib.http import JsonRPCResponse
from contrib.permissions import has_permissions
from contrib.utils import decode_token, encode_token, get_body
from core.models import KeycloakUserManager
from main import Log


def authenticate_user(request, encoded_token: str, permissions: list) -> bool:
    try:
        # decoded_token = decode_token(encoded_token)
        refreshed_token, user = KeycloakUserManager.authenticate_token(encoded_token)
    except Exception as e:
        Log.error("authenticate_user", e)
        return False

    if not refreshed_token:
        return False

    if not has_permissions(user, permissions):
        return False

    request.keycloak_encoded_token = encode_token(refreshed_token)
    request.keycloak_token = refreshed_token
    request.keycloak_user = user
    return True


def keycloak_authenticate(position, *permissions):
    """Authenticates a token passed in the request body. If the authentication fails returns an
    unauthorized response.

    Args:
        position (int): Position of the token in params.
        *args: Permissions required for the view.

    Example:
        @keycloak_authenticate(1)
        def my_view(request):
            pass

        @keycloack_authenticate(1, "superuser")
        def my_other_view(request):
            pass
    """

    def decorator(func):
        def authenticate(request, *args, **kwargs):
            try:
                body = get_body(request)
                params = body["params"]
                token = params[position]
            except:
                return JsonRPCResponse(error="Invalid authentication token", status=401)

            authenticated = authenticate_user(request, token, permissions)
            if not authenticated:
                return JsonRPCResponse(error="Unauthorized", status=403)

            return func(request, *args, **kwargs)

        return authenticate

    return decorator


def keycloak_authenticate_get(name, *permissions):
    """Authenticates a token passed in the query string. If the authentication fails returns an
    unauthorized response.

    Args:
        name (str): Name of the query string parameter with the token.
        *args: Permissions required for the view.

    Example:
        @keycloak_authenticate("access_token")
        def my_view(request):
            pass

        @keycloack_authenticate("access_token", "superuser")
        def my_other_view(request):
            pass
    """

    def decorator(func):
        def authenticate(request, *args, **kwargs):
            token = request.GET.get(name)
            if token is None:
                return JsonRPCResponse(error="Invalid authentication token", status=401)

            authenticated = authenticate_user(request, token, permissions)
            if not authenticated:
                return JsonRPCResponse(error="Unauthorized", status=403)

            return func(request, *args, **kwargs)

        return authenticate

    return decorator


def keycloak_authenticate_header(*permissions):
    """Authenticates a  keycloak token passed in the Authorization header. If the authentication
    fails returns an unauthorized response.

    Args:
        *args: Permissions required for the view.

    Example:
        @keycloak_authenticate("access_token")
        def my_view(request):
            pass

        @keycloack_authenticate("access_token", "superuser")
        def my_other_view(request):
            pass
    """

    def decorator(func):
        def authenticate(request, *args, **kwargs):
            token = request.headers.get('AUTHORIZATION')
            # token = request.META.get("HTTP_AUTHORIZATION")
            if token is None:
                return JsonRPCResponse(error="Unauthorized", status=401)
            token_regex = re.compile(r"^bearer (?P<token>.+)$", re.I)
            match = token_regex.match(token)
            if match is None:
                return JsonRPCResponse(error="Invalid authentication token", status=401)

            token = match.group("token")
            authenticated = authenticate_user(request, token, permissions)
            if not authenticated:
                return JsonRPCResponse(error="Forbiden", status=401)

            return func(request, *args, **kwargs)

        return authenticate

    return decorator


def verify_jsonrpc(match={}, params_length=None):
    """Method decorator. Verifies that the body of the request contains the neccesary JSONRPC
    fields. The JSONRPC object is added to the request if the verification succeeds.

    Args:
        match (dict): Any key in the dictionary must have a perfect match in the body. Defaults to
            an empty dictionary. If the field value is a list the body field must be one of the
            values in the list.
        params_length (int): Length of the params

    Example:
        @verify_jsonrpc()
        def view(request):
            # Body must have the fields "id", "jsonrpc", "method", and "params". "jsonrpc" must be
            # "2.0"
            # JSONRPC object is accesible in request.jsonrpc
            pass

        @verify_jsonrpc({"method": "executekw"})
        def another_view(request):
            # Similar to the previus example but "method" must also be equal to "executekw"
            pass
    """

    def decorator(func):
        def verify(request, *args, **kwargs):
            body = get_body(request)
            values = {**match, **{"jsonrpc": "2.0"}}

            if body:
                errors = []
                fields = ["id", "jsonrpc", "method", "params"]
                for key in body:
                    if key in fields:
                        fields.remove(key)
                        if (
                            key == "params"
                            and params_length
                            and len(body["params"]) < params_length
                        ):
                            errors.append(JsonRPCException("One ore more parameters missing"))
                        elif key in values and isinstance(values[key], list):
                            if body[key] not in values[key]:
                                errors.append(JsonRPCException(f"Invalid {key}"))
                        elif key in values:
                            if values[key] != body[key]:
                                errors.append(JsonRPCException(f"Invalid {key}"))
                    else:
                        errors.append(JsonRPCException(f"{key} is not a valid field."))
                if len(fields) > 0:
                    for key in fields:
                        errors.append(JsonRPCException(f"field '{key}' is required"))
                if errors:
                    return JsonRPCResponse(error=errors, status=400)
                request.jsonrpc = body
            else:
                return JsonRPCResponse(
                    error="Request does not contains a JSONRPC object", status=400
                )

            return func(request, *args, **kwargs)

        return verify

    return decorator
