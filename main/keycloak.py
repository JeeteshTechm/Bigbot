from keycloak import KeycloakOpenID
from keycloak import KeycloakAdmin
import json
import base64
import time


def base64_encode(string):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.b64encode(string_bytes)
    return base64_bytes.decode("ascii")

def base64_decode(string):
    base64_bytes = string.encode("ascii")
    string_bytes = base64.b64decode(base64_bytes)
    return string_bytes.decode("ascii")

class KeyclaokController:

    def __init__(self):
        server_url = 'https://login.igotbot.com/auth/'
        realm_name = 'test02'
        client_id = 'main'
        client_secret_key = 'aa12dcae-02df-43e4-8f2a-36e8212f69c1'
        admin_username = "admin@igotbot.com"
        admin_password = "PyMpw47dmfr7r"
        self.keycloak_openid = KeycloakOpenID(server_url=server_url,client_id=client_id,
                                              realm_name=realm_name,client_secret_key=client_secret_key)
        self.keycloak_admin = KeycloakAdmin(server_url=server_url,username=admin_username,
                                              password=admin_password,realm_name=realm_name,verify=True)
        pass

    @staticmethod
    def openid_token(username, password):
        try:
            kc = KeyclaokController()
            token = kc.keycloak_openid.token(username, password)
            token['created_at'] = time.time()
            token_string = json.dumps(token)
            return base64_encode(token_string)
        except Exception as e:
            KeyclaokController.log_error(e)

    @staticmethod
    def load_token(kc, token_encoded):
        token = json.loads(base64_decode(token_encoded))
        print(token['refresh_expires_in'],'==================refresh_expires_in==================')
        if token['created_at']+token['expires_in'] > time.time():
            return token
        token = kc.keycloak_openid.refresh_token(token['refresh_token'])
        return token

    @staticmethod
    def authenticate(token_encoded):
        try:
            kc = KeyclaokController()
            token  = KeyclaokController.load_token(kc, token_encoded)
            userinfo = kc.keycloak_openid.userinfo(token['access_token'])
            km = KeycloakUserModel()
            km.email = userinfo.get('email')
            km.first_name = userinfo.get('given_name')
            km.last_name = userinfo.get('family_name')
            km.email_verified = userinfo.get('email_verified')
            km.username = userinfo.get('preferred_username')
            km.user_id = kc.keycloak_admin.get_user_id(km.username)
            for item in kc.keycloak_admin.get_user_groups(user_id=km.user_id):
                km.groups.append(item.get('name'))
            return km
        except Exception as e:
            KeyclaokController.log_error(e)

    @staticmethod
    def logout(token_encoded):
        try:
            kc = KeyclaokController()
            token  = KeyclaokController.load_token(kc, token_encoded)
            res = kc.keycloak_openid.logout(token['refresh_token'])
            return True
        except Exception as e:
            KeyclaokController.log_error(e)

    @staticmethod
    def log_error(obj):
        print('KeyclaokController: ',obj)


class KeycloakUserManager:

    def __init__(self):
        pass

    def filter(self, **kwargs):
        ku = KeycloakUserModel()
        return

class KeycloakUserModel:

    objects = KeycloakUserManager()

    def __init__(self):
        self.username = None
        self.first_name = None
        self.last_name = None
        self.email = None
        self.email_verified = None
        self.groups = []


    def serialize(self):
        return {
            'username':self.username,
            'first_name':self.first_name,
            'last_name':self.last_name,
            'email':self.email,
            'email_verified':self.email_verified,
            'groups':self.groups,
        }