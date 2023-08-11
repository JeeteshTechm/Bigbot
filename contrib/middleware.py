import json
import re

from contrib.utils import encode_token
from core.models import KeycloakUserManager
from main import Log


token_regex = re.compile(r"^bearer (?P<token>.+)$", re.I)


class KeycloakUserMiddleware:
    """Checks if the request POST parameters contains a keycloack access token, and if it does adds
    keycloak user to the request object. The refreshed token is added to the response headers as
    "Access-Token".
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = request.META.get("HTTP_AUTHORIZATION")
        refreshed_token = None
        if token:
            match = token_regex.match(token)
            if match:
                token = match.group("token")
                try:
                    refreshed_token, user = KeycloakUserManager.authenticate_token(token)
                    if user is None:
                        refreshed_token = None
                except Exception as e:
                    Log.error("KeycloakMiddleware",e)
                    refresh_token = None

        response = self.get_response(request)

        token = getattr(request, "keycloak_encoded_token", None)
        if token:
            response["Access-Token"] = token
        elif refreshed_token:
            response["Access-Token"] = encode_token(refreshed_token)

        return response
