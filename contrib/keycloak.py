import base64
import datetime
import json
import time

from django.conf import settings
from keycloak import KeycloakAdmin, KeycloakOpenID
import requests

from contrib import utils
from main import Log


class KeycloakController:
    _singleton = None

    def __init__(self):
        server_url = settings.KEYCLOAK_CONFIG["KEYCLOAK_SERVER_URL"]
        realm_name = settings.KEYCLOAK_CONFIG["KEYCLOAK_REALM"]
        client_id = settings.KEYCLOAK_CONFIG["KEYCLOAK_CLIENT_ID"]
        client_secret_key = settings.KEYCLOAK_CONFIG["KEYCLOAK_CLIENT_SECRET_KEY"]
        admin_username = settings.KEYCLOAK_CONFIG["KEYCLOAK_ADMIN_USERNAME"]
        admin_password = settings.KEYCLOAK_CONFIG["KEYCLOAK_ADMIN_PASSWORD"]

        try:
            self.keycloak_openid = KeycloakOpenID(
                client_id=client_id,
                client_secret_key=client_secret_key,
                realm_name=realm_name,
                server_url=server_url,
            )
        except:
            pass

        try:
            self.keycloak_admin = KeycloakAdmin(
                auto_refresh_token=["delete", "get", "post", "put"],
                password=admin_password,
                realm_name=realm_name,
                server_url=server_url,
                username=admin_username,
                verify=True,
            )
        except:
            pass

    @staticmethod
    def authenticate(token_encoded):
        try:
            kc = KeycloakController.get_singleton()
            token = KeycloakController.load_token(kc, token_encoded)
            userinfo = kc.keycloak_openid.userinfo(token["access_token"])
            km = KeycloakUserModel()
            km.email = userinfo.get("email")
            km.first_name = userinfo.get("given_name")
            km.last_name = userinfo.get("family_name")
            km.email_verified = userinfo.get("email_verified")
            km.username = userinfo.get("preferred_username")
            km.user_id = kc.keycloak_admin.get_user_id(km.username)
            for item in kc.keycloak_admin.get_user_groups(user_id=km.user_id):
                km.groups.append(item.get("name"))
            return km
        except Exception as e:
            KeycloakController.log_error(e)

    @staticmethod
    def get_singleton():
        """Returns a singleton instance of KeycloakController"""
        if KeycloakController._singleton is None:
            kc = KeycloakController()
            KeycloakController._singleton = kc
            print("KeycloakController => Singleton Created", kc)
        print("KeycloakController => Singleton Fetched", KeycloakController._singleton)
        return KeycloakController._singleton

    @staticmethod
    def is_user_in_role(user_id, role_name):
        """Checks if a user is member of a keycloak role

        Args:
            user_id (uuid): keycloak user id
            role_name (str): keycloak role name

        Returns:
            True if user is a member, False otherwise
        """
        is_member = False
        kc = KeycloakController.get_singleton()
        try:
            members = kc.keycloak_admin.get_realm_role_members(role_name)
            for member in members:
                if member["id"] == user_id:
                    is_member = True
                    break
        except:
            pass
        return is_member

    @staticmethod
    def load_token(kc, token_encoded):
        token = json.loads(utils.base64_decode(token_encoded))
        print(
            token["refresh_expires_in"],
            "==================refresh_expires_in==================",
        )
        if token["created_at"] + token["expires_in"] > time.time():
            return token
        token = kc.keycloak_openid.refresh_token(token["refresh_token"])
        return token

    @staticmethod
    def logout(token_encoded):
        try:
            kc = KeycloakController.get_singleton()
            token = KeycloakController.load_token(kc, token_encoded)
            res = kc.keycloak_openid.logout(token["refresh_token"])
            return True
        except Exception as e:
            Log.error("KeycloackController", e)

    @staticmethod
    def log_error(obj):
        print("KeycloakController: ", obj)

    @staticmethod
    def openid_token(username, password):
        try:
            kc = KeycloakController.get_singleton()
            token = kc.keycloak_openid.token(username, password)
            token["created_at"] = time.time()
            token["realm"] = ""
            print("token =>", token)
            token_string = json.dumps(token)
            return utils.base64_encode(token_string)
        except Exception as e:
            KeycloakController.log_error(e)


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


class RealmController:
    """Controller to manage a single realm"""

    def __init__(
        self,
        realm,
        admin="",
        password="",
        client="internal-realm-admin",
        init_admin=True,
    ):
        """
        Args:
            admin (str): Realm's "administrator" username.
            password (str): Realm's "administrator" password.
        """
        self.client = client
        self.realm = realm
        self.server_url = settings.MASTER_REALM["KEYCLOAK_SERVER_URL"]
        if self.server_url[-1] == "/":
            self.server_url = self.server_url[:-1]
        if init_admin:
            self.token = self.login(admin, password)
        else:
            self.token = None

    def add_user_to_group(self, user_id, group_id, **kwargs):
        """Adds a new user to realm, new user will be part of the superuser
        group.
        """
        self.put(f"users/{user_id}/groups/{group_id}", **kwargs)

    def create_client(self, client_id, payload={}, **kwargs):
        """Creates a new client. Returns client's id"""
        self.post(
            "clients",
            json={**payload, "clientId": client_id, "name": "${" + client_id + "}"},
            **kwargs,
        )
        client = self.get(f"clients?clientId={client_id}", **kwargs)[0]
        return client["id"]

    def create_group(self, name):
        name = name.lower()
        self.post("groups", json={"name": name})
        groups = self.get_groups()
        for group in groups:
            if group["name"] == name:
                return group

    def create_protocol_mapper(self, client_id, name, claim_name, mapper_type, config={}, **kwargs):
        """Creates a new protocol mapper for the client

        Args:
            client_id (str): Client's UUID.
            name (str): Name for the new mapper.
            claim_name (str): String used in the access token, userinfo, etc.
            mapper_type (str): Mapper type. Check the keycloak documentation for more details.
            config (dict): Extra config for the mapper.

        Example:
            create_protocol_mapper(
                "db12653f-54eb-49af-ae0c-32a8371f3747",
                "GroupMapper",
                "groups",
                "oidc-group-membership-mapper",
                {
                    "full.path": "false",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "true"
                },
            )
        """
        config["claim.name"] = claim_name
        self.post(
            f"clients/{client_id}/protocol-mappers/models",
            json={
                "name": name,
                "protocol": "openid-connect",
                "protocolMapper": mapper_type,
                "config": config,
            },
            **kwargs,
        )

    def create_user(
        self,
        email,
        required_actions=["VERIFY_EMAIL", "UPDATE_PASSWORD", "UPDATE_PROFILE"],
        *,
        params={},
        **kwargs,
    ):
        """Add new user to realm. Returns the new user representation"""
        self.post(
            "users",
            json={
                **params,
                "email": email,
                "username": email,
                "enabled": True,
                "requiredActions": required_actions,
            },
            **kwargs,
        )
        users = self.get(f"users?email={email}", **kwargs)
        user = users[0]
        return user

    def delete(self, path, **kwargs):
        """Shorthand for self.request("DELETE", ...)"""
        return self.request("DELETE", path, **kwargs)

    def get(self, path, **kwargs):
        """Shorthand for self.request("GET", ...)"""
        return self.request("GET", path, **kwargs)

    def get_clients(self, **kwargs):
        return self.get("clients", **kwargs)

    def get_certs(self):
        return self.get("protocol/openid-connect/certs")

    def get_groups(self, **kwargs):
        return self.get("groups", **kwargs)

    def get_groups_by_name(self, *group_names, **kwargs):
        """Returns representation of group"""
        result = []
        groups = self.get("groups", **kwargs)
        for group in groups:
            for name in group_names:
                if name == group["name"]:
                    result.append(group)
        return result

    def get_or_create_groups(self, groups, **kwargs):
        """
        Args:
            groups (list): List of strings, where each string is the name of the group.
            **kwargs: Extra parameters fro teh request.
        """
        available_groups = self.get_groups()
        result = []

        for group_name in groups:
            group = None
            for group_representation in available_groups:
                if group_representation["name"] == group_name.lower():
                    group = group_representation
                    break

            if group:
                result.append(group)
            else:
                group = self.create_group(group_name)
                result.append(group)

        return result

    def get_public_key(self, **kwargs):
        """Returns the realm's public key"""
        data = self.get("", **kwargs)
        return data["public_key"]

    def get_user(self, user_id, **kwargs):
        try:
            user = self.get(f"users/{user_id}", **kwargs)
            groups = self.get(f"users/{user_id}/groups", **kwargs)
            for index, group in enumerate(groups):
                groups[index] = group["name"]
            return {
                "email": user["email"],
                "emailVerified": user["emailVerified"],
                "enabled": user["enabled"],
                "firstName": user["firstName"],
                "groups": groups,
                "id": user["id"],
                "lastName": user["lastName"],
                "username": user["username"],
            }
        except Exception as e:
            Log.error("RealmController.get_user", e)

    def get_user_groups(self, user_id, **kwargs):
        groups = self.get(f"users/{user_id}/groups")
        return groups

    def get_users(self, **kwargs):
        """Get the full user data"""
        return self.get("users", **kwargs)

    def impersonate_user(self, user_id) -> dict:
        """Impersonates a user in realm.

        Args:
            user_id (str): UUID of the users that is going to be impersonated.

        Returns:
            dict: Access token.
        """
        token = self.post(
            f"realms/{self.realm}/protocol/openid-connect/token",
            data={
                "client_id": "internal-realm-admin",
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "requested_subject": user_id,
                "subject_token": self.token["access_token"],
            },
            full_url=True,
        )
        token["created_at"] = time.time()
        token["rlm"] = self.realm
        return token

    def login(self, username, password):
        """Signs in an user

        Returns:
            dict: The authentication response.
        """
        token = self.post(
            "protocol/openid-connect/token",
            data={
                "client_id": self.client,
                "grant_type": "password",
                "password": password,
                "username": username,
            },
        )
        token["created_at"] = time.time()
        token["rlm"] = self.realm
        return token

    def logout(self, token):
        """Signs out an user"""
        self.post(
            "protocol/openid-connect/logout",
            data={"client_id": self.client, "refresh_token": token["refresh_token"]},
        )

    def post(self, path, **kwargs):
        """Shorthand for self.request("POST", ...)"""
        return self.request("POST", path, **kwargs)

    def put(self, path, **kwargs):
        """Shorthand for self.request("PUT", ...)"""
        return self.request("PUT", path, **kwargs)

    def refresh_token(self, token):
        if token["created_at"] + token["expires_in"] - 60 < time.time():
            token = requests.post(
                f"{self.server_url}/realms/{self.realm}/protocol/openid-connect/token",
                data={
                    "client_id": self.client,
                    "grant_type": "refresh_token",
                    "refresh_token": token["refresh_token"],
                },
            ).json()
            token["created_at"] = time.time()
            token["rlm"] = self.realm
        return token

    def request(self, method, path, *, full_url=False, realm=None, skip_exists=False, **kwargs):
        if len(path) > 0 and path[0] == "/":
            path = path[1:]

        if realm is None:
            realm = self.realm

        if not full_url:
            url = f"realms/{realm}/{path}"
            token = getattr(self, "token", None)
            if token:
                self.token = self.refresh_token(token)
                headers = kwargs.get("headers", {})
                headers["Authorization"] = f"Bearer {self.token['access_token']}"
                kwargs["headers"] = headers
                url = f"admin/{url}"
            url = f"{self.server_url}/{url}"
        else:
            url = f"{self.server_url}/{path}"
            token = getattr(self, "token", None)
            if token:
                self.token = self.refresh_token(token)
                headers = kwargs.get("headers", {})
                headers["Authorization"] = f"Bearer {self.token['access_token']}"
                kwargs["headers"] = headers

        if url[-1] == "/":
            url = url[:-1]

        response = requests.request(method, url, **kwargs)

        if response.status_code == 409 and skip_exists:
            Log.warning(
                "KeycloakController.request", "Resource already exists", method, url, kwargs
            )
        else:
            response.raise_for_status()

        try:
            return response.json()
        except:
            return response.text

    def reset_password(self, user_id, password, **kwargs):
        self.put(
            f"users/{user_id}/reset-password",
            json={"type": "password", "temporary": False, "value": password},
            **kwargs,
        )

    def send_mail_verification(self, user_id, client_id=None, redirect_uri=None, **kwargs):
        """Sends a verification email to user"""
        params = {}
        if client_id:
            params["client_id"] = client_id
        if redirect_uri:
            params["redirect_uri"] = redirect_uri
        self.put(f"users/{user_id}/send-verify-email", params=params, **kwargs)

    def update_user_groups(self, user_id, groups, **kwargs):
        """Adds and removes the user from groups"""
        new_groups = self.get_or_create_groups(groups, **kwargs)
        user_groups = self.get_user_groups(user_id, **kwargs)
        add = []
        remove = []

        def get_group(name):
            for group in new_groups:
                if group["name"] == name:
                    return group

        if len(user_groups) == 0:
            add = new_groups
        else:
            for group in user_groups:
                found = False
                for group_name in groups:
                    if group["name"] == group_name:
                        found = True
                        break

                remove_group = True
                for new_group in new_groups:
                    if new_group["name"] == group["name"]:
                        remove_group = False
                        break

                if not found:
                    add.append(group_name)
                if remove_group and group["name"] != "__superuser__":
                    remove.append(group)

            add = list(map(get_group, add))

        for group in add:
            self.put(f"users/{user_id}/groups/{group['id']}", **kwargs)
        for group in remove:
            self.delete(f"users/{user_id}/groups/{group['id']}", **kwargs)

    def update_user_credentials(self, user_id, enabled=None, groups=None, **kwargs):
        data = {}

        if isinstance(enabled, bool):
            data["enabled"] = enabled
            if enabled and "__operator__" not in groups:
                groups.append("__operator__")
            elif not enabled and "__operator__" in groups:
                groups = list(filter(lambda x: x != "__operator__", groups))

        self.update_user_groups(user_id, groups, **kwargs)
        self.put(f"users/{user_id}", json=data, **kwargs)


class MasterRealmController(RealmController):
    """Special controller for the master realm, the master realm has access to other realms"""

    def __init__(self):
        super().__init__(
            settings.MASTER_REALM["KEYCLOAK_REALM"],
            settings.MASTER_REALM["KEYCLOAK_ADMIN_USERNAME"],
            settings.MASTER_REALM["KEYCLOAK_ADMIN_PASSWORD"],
            settings.MASTER_REALM["KEYCLOAK_CLIENT_ID"],
        )

    def create_realm(self, realm_name):
        """Creates a new realm using the template realm as a base.
        Returns the realm's id.
        """
        realm, groups = self.get_template_realm()

        realm["id"] = realm_name
        realm["realm"] = realm_name

        Log.info("create_realm", f"template realm fetched")

        self.post("admin/realms", full_url=True, json=realm, skip_exists=True)

        Log.info("create_realm", f"{realm_name} created")

        groups = self.get_groups(realm="template")
        for group in groups:
            self.post("groups", json={"name": group["name"]}, realm=realm_name, skip_exists=True)
        Log.info("create_realm", f"groups created")

        client = self.get("clients?clientId=account", realm=realm_name)[0]
        Log.info("create_realm", f"account client fetched")

        self.put(
            f"clients/{client['id']}",
            json={
                "enabled": True,
                "standardFlowEnabled": True,
                "implicitFlowEnabled": False,
                "directAccessGrantsEnabled": False,
                "serviceAccountsEnabled": True,
                "authorizationServicesEnabled": False,
                "consentRequired": False,
                "fullScopeAllowed": True,
            },
            realm=realm_name,
            skip_exists=True,
        )
        Log.info("create_realm", f"account client updated")

        client_id = self.create_client(
            "internal-realm-admin",
            {
                "enabled": True,class RealmController:
    def __init__(self, realm, admin_username, admin_password, client_id):
        # implementation details

    def create_realm(self, realm_name):
        # implementation details

    def delete_realm(self, realm_id):
        # implementation details

    def get_realm(self, realm_id):
        # implementation details

class MasterRealmController(RealmController):
    def __init__(self):
        # implementation details

    def create_realm(self, realm_name):
        # implementation details

    def get_template_realm(self):
        # implementation details

    def setup_admin_account(self, realm, admin_email="admin@bigbot.ai"):
        # implementation details

                "publicClient": True,
                "directAccessGrantsEnabled": True,
                "standardFlowEnabled": False,
            },
            realm=realm_name,
            skip_exists=True,
        )
        Log.info("create_realm", f"internal-realm-admin client created")

        self.create_protocol_mapper(
            client_id,
            "GroupMapper",
            "groups",
            "oidc-group-membership-mapper",
            {
                "full.path": "false",
                "id.token.claim": "true",
                "access.token.claim": "true",
                "userinfo.token.claim": "true",
            },
            realm=realm_name,
            skip_exists=True,
        )
        Log.info("create_realm", f"GroupMapper created")

        return realm["id"]

    def delete_realm(self, realm_id):
        """Deletes a realm"""
        self.make_delete_request("admin/realms/{}".format(realm_id))
        print("===== Realm {} deleted =====".format(realm_id))

    def get_template_realm(self):
        """Gets the Template realm"""
        realm = self.get("", realm="template")
        realm["smtpServer"]["password"] = settings.MASTER_REALM["KEYCLOAK_EMAIL_SERVER_PASSWORD"]
        groups = self.get("/groups", realm="template")
        return realm, groups

    def setup_admin_account(self, realm, admin_email="admin@bigbot.ai"):
        """Creates a new admin account for realm.

        Args:
            realm (str): realmId.
            admin_email (str): email  for the admin user.

        Returns:
            Tuple[str, str, str]: A tuple with the user's id, email, and password.
        """
        from django.contrib.auth.models import BaseUserManager

        password = BaseUserManager.make_random_password(None, 16)

        user = self.create_user(
            admin_email, [], params={"emailVerified": True}, realm=realm, skip_exists=True
        )
        self.reset_password(user["id"], password, realm=realm)

        realm_management_client = self.get(f"clients?clientId=realm-management", realm=realm)[0]
        role_mappings = self.get(
            f"users/{user['id']}/role-mappings/clients/{realm_management_client['id']}/available",
            realm=realm,
        )

        self.post(
            f"users/{user['id']}/role-mappings/clients/{realm_management_client['id']}",
            realm=realm,
            json=role_mappings,
        )

        return user["id"], admin_email, password
