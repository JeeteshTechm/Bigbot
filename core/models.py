from __future__ import unicode_literals
import datetime
import json
import random
import string
import threading
import time
from urllib.parse import urlparse
import uuid

from deprecated import deprecated
from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import models
from django.db.models.functions import Now
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from django_middleware_global_request.middleware import get_request
import gitlab
import jwt
import requests

from contrib import mixin, utils
from contrib.keycloak import MasterRealmController, RealmController
from main import Log

from .managers import UserManager


class KeycloakRealm(models.Model):
    """Links a Project to a Keycloak instance

    Attributes:
        admin (str): Realm administrator email.
        password (str): Realm administrator password.
        realm (str): Realm id, e.g. 'client-realm'
    """

    admin = models.EmailField(default="admin@igotbot.com", blank=True, null=True)
    password = models.TextField(default="", blank=True, null=True)
    public_key = models.TextField(default=None, blank=True, null=True)
    realm = models.CharField(max_length=128, unique=True)

    def __repr__(self):
        return f"<KeycloakRealm: {self.realm}>"

    def __str__(self):
        return self.__repr__()

    def check_status(self):
        """Checks if a realm is online"""
        try:
            rc = RealmController(self.realm, self.admin, self.password)
            return True
        except Exception as e:
            Log.error("KeycloakRealm.check_realm", e)
            return False

    def clone_user(self, manager):
        """Clones an user to realm"""
        try:
            rc = RealmController(self.realm, self.admin, self.password)
            user = rc.create_user(manager.email, [])
            KeycloakUser.objects.create(manager=manager, realm=self, uuid=user["id"])
        except Exception as e:
            Log.error("KeycloakRealm.clone_user", e)

    @staticmethod
    def create(realm_name):
        realm = KeycloakRealm.get_singleton(realm_name)
        return realm

    def create_user(email):
        """Creates a new user in reaml"""
        try:
            rc = RealmController(self.realm, self.admin, self.password)
            user = rc.create_user(email)
            keycloak_user = KeycloakUser.objects.create(realm=self, uuid=user["id"])
            manager = KeycloakUserManager.objects.filter(email=email).first()
            if manager is None:
                KeycloakUserManager.create(keycloak_user, user)
            else:
                keycloak_user.manager = manager
                keycloak_user.save()
        except Exception as e:
            Log.error("KeycloakRealm.create_user", e)

    @staticmethod
    def delete_realm(realm_name):
        realm = KeycloakRealm.get_singleton(realm_name)
        realm.delete()

    def get_clients(self):
        rc = RealmController(self.realm, self.admin, self.password)
        return rc.get_clients()

    def get_public_key(self):
        if self.public_key is None or self.public_key == "":
            rc = RealmController(self.realm, init_admin=False)
            public_key = rc.get_public_key()
            self.public_key = f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----"
            self.save()
        return self.public_key

    @staticmethod
    def get_singleton(realm_name):
        realm, created = KeycloakRealm.objects.get_or_create(realm=realm_name)
        if not created:
            created = not realm.check_status()
        if created:
            mc = MasterRealmController()
            mc.create_realm(realm_name)
            _, admin, password = mc.setup_admin_account(realm_name)
            realm.admin = admin
            realm.password = password
            realm.save()
        return realm

    def get_user(self, user_id):
        rc = RealmController(self.realm, self.admin, self.password)
        return rc.get_user(user_id)

    def impersonate_user(self, user_id: str) -> dict:
        try:
            rc = RealmController(self.realm, self.admin, self.password)
            token = rc.impersonate_user(user_id)
            return token
        except Exception as e:
            Log.error("KeycloakRealm.impersonate_user", e)

    def invite_user(self, email, client_id=None, redirect_uri=None):
        try:
            rc = RealmController(self.realm, self.admin, self.password)
            user = rc.create_user(email)
            keycloak_user = KeycloakUser.objects.create(realm=self, uuid=user["id"])
            manager = KeycloakUserManager.objects.filter(email=email).first()
            if manager is None:
                KeycloakUserManager.create(keycloak_user, user)
            else:
                keycloak_user.manager = manager
                keycloak_user.save()
            rc.send_mail_verification(user["id"], client_id, redirect_uri)
            return True
        except Exception as e:
            Log.error("KeycloakRealm.create_user", e)

    @staticmethod
    def link(project_id, realm_name):
        project = Project.objects.get(id=project_id)
        realm = KeycloakRealm.get_singleton(realm_name)
        realm.project = project
        realm.save()

    def list_users(self):
        rc = RealmController(self.realm, self.admin, self.password)
        users = rc.get_users()
        result = []
        for user in users:
            email = user.get("email")
            if email == self.admin:
                continue
            result.append(
                {
                    "id": user["id"],
                    "email": email,
                    "emailVerified": user.get("emailVerified", False),
                    "enabled": user.get("enabled", False),
                    "firstName": user.get("firstName", ""),
                    "groups": user.get("groups", []),
                    "lastName": user.get("lastName", ""),
                    "username": user.get("username", ""),
                }
            )
        return result

    def parse_token(self, token):
        """Parses an access_token. Returns None if the has expired or if it is not valid"""
        public_key = self.get_public_key()
        try:
            access_token = token["access_token"]
            return jwt.decode(access_token, public_key, algorithms=["RS256"], audience="account")
        except Exception as e:
            Log.error("KeycloakRealm.parse_token", e)

    def sync(self):
        """Synchronizes the realm users with this application. Creates a KeycloakUserManager if none
        exists for the user.
        """
        rc = RealmController(self.realm, self.admin, self.password)
        users = rc.get_users()
        for user in users:
            keycloak_user = KeycloakUser.objects.filter(uuid=user["id"]).first()

            if keycloak_user is None:
                keycloak_user = KeycloakUser.objects.create(realm=self, uuid=user["id"])
                manager = KeycloakUserManager.create(keycloak_user, user)
            else:
                manager = keycloak_user.manager
                if manager is None:
                    manager = KeycloakUserManager.create(keycloak_user, user)

    @staticmethod
    def unlink(project_id):
        project = Project.objects.get(id=project_id)
        realm = KeycloakRealm.objects.get(project=project)
        realm.project = None
        realm.save()


class KeycloakUser(models.Model):
    """Basic data needed to manage a Keycloak user.

    Attributes:
        manager: KeycloakUserManager instance used to manage the user.
        realm: User's realm.
        uuid: User's UUID.
    """

    manager = models.ForeignKey(
        "core.KeycloakUserManager",
        related_name="keycloak_users",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    realm = models.ForeignKey(
        KeycloakRealm,
        related_name="keycloak_users",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
    )
    uuid = models.UUIDField()

    def __repr__(self):
        realm = self.realm
        if self.manager:
            return f"<KeycloakUser ({realm.realm}): {self.manager.email}>"
        return f"<KeycloakUser ({realm.realm}): {self.uuid}>"

    def __str__(self):
        return self.__repr__()

    @property
    def project(self):
        return Project.objects.filter(keycloak_realm=self.realm).first()


class KeycloakUserManager(models.Model):
    """Maps multiple keycloak users to a "main" user. Any user linked to the main user can
    impersonate the other linked users, including the main user.

    Attributes:
        email (str): Unique email for the user. Will be used for authentication.
        phone (str): Unique phone number for the user.
        main: Instance of core.models.KeycloakUser. Used for authentication.
    """

    email = models.EmailField(unique=True, blank=True, null=True)
    main = models.OneToOneField(
        KeycloakUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    phone = models.CharField(max_length=100, unique=True, blank=True, null=True)

    def __repr__(self):
        if self.email:
            return self.email
        return self.phone

    def __str__(self):
        return self.__repr__()

    @property
    def realm(self):
        return self.main.realm.realm

    @property
    def uuid(self):
        return self.main.uuid

    @staticmethod
    def authenticate(email, password):
        """Authenticates a user"""
        manager = KeycloakUserManager.objects.filter(email=email).first()
        if manager:
            try:
                realm = manager.main.realm
                rc = RealmController(realm.realm, init_admin=False)
                token = rc.login(email, password)
                return utils.encode_token(token)
            except Exception as e:
                Log.error("KeycloakUserManager", "auhtenticate", e)
        return None

    @staticmethod
    def authenticate_token(encoded_token):
        """Authenticates an existing token"""
        token = utils.decode_token(encoded_token)
        realm = KeycloakRealm.objects.filter(realm=token["rlm"]).first()

        try:
            user = realm.parse_token(token)
            if user is None:
                rc = RealmController(realm.realm, init_admin=False)
                token = rc.refresh_token(token)
                user = realm.parse_token(token)
            return token, {
                "email": user["email"],
                "email_verified": user["email_verified"],
                "last_name": user.get("family_name", ""),
                "first_name": user.get("given_name", ""),
                "groups": user.get("groups", []),
                "id": user["sub"],
                "username": user["preferred_username"],
            }
        except Exception as e:
            Log.error("KeycloakUserManager.authenticate_token", e)
        return None, None

    @staticmethod
    def create(keycloak_user, user_representation):
        """
        Args:
            keycloak_user: KeycloakUser instance.
            user_representation (dict): Keycloak user data.
        """
        manager = KeycloakUserManager.objects.filter(email=user_representation["email"]).first()
        if manager is None:
            manager = KeycloakUserManager.objects.create(
                email=user_representation["email"],
                main=keycloak_user,
            )
        keycloak_user.manager = manager
        keycloak_user.save()
        return manager

    @staticmethod
    def get_user(user, user_id):
        keycloak_user = KeycloakUser.objects.filter(uuid=user["id"]).first()
        if keycloak_user is None:
            return None
        if keycloak_user.realm is None:
            return None
        return keycloak_user.realm.get_user(user_id)

    @staticmethod
    def get_user_project(user):
        keycloak_user = KeycloakUser.objects.filter(uuid=user["id"]).first()
        if keycloak_user is None:
            return None
        return keycloak_user.project

    @staticmethod
    def invite_user(user, email, client_id=None, redirect_uri=None):
        keycloak_user = KeycloakUser.objects.filter(uuid=user["id"]).first()
        if keycloak_user is None:
            return None
        realm = keycloak_user.realm
        if realm is None:
            return None
        return realm.invite_user(email, client_id, redirect_uri)

    @staticmethod
    def list_users(user):
        keycloak_user = KeycloakUser.objects.filter(uuid=user["id"]).first()
        if not keycloak_user:
            return None
        if not keycloak_user.realm:
            return None
        if keycloak_user:
            return keycloak_user.realm.list_users()

    @staticmethod
    def logout(user, token):
        """Logs out an authenticated user

        Args:
            user (dict): User representation of the authenticated user.
            token (dict): Authentication token.
        """
        keycloak_user = KeycloakUser.objects.filter(uuid=user["id"]).first()
        if not keycloak_user and keycloak_user.realm.realm:
            return None
        try:
            realm = keycloak_user.realm
            rc = RealmController(realm.realm, init_admin=False)
            return True
        except Exception as e:
            Log.error("KeycloakUserManager", "logout", e)

    @staticmethod
    def list_instances(token, user):
        """Returns a list projects the user has access

        Args:
            token (dict): User authentication token.
            user (dict): User representation of the authenticated user.
        """
        keycloak_user = KeycloakUser.objects.filter(uuid=user["id"]).first()
        if keycloak_user is None:
            return None
        if keycloak_user.manager is None:
            return None
        projects = set()
        users = KeycloakUser.objects.filter(manager=keycloak_user.manager)
        current = None
        for user in users:
            project = user.project
            if project:
                projects.add(project)
                if project.keycloak_realm.realm == token["rlm"]:
                    current = {
                        "instance_url": project.instance_uri,
                        "name": project.name,
                        "status": project.status,
                    }
        return [
            {"instance_uri": project.instance_uri, "name": project.name, "status": project.status}
            for project in projects
        ], current

    def save(self, *args, **kwargs):
        if self.main is None:
            self.main = KeycloakUser.objects.filter(manager=self).first()
        super().save(*args, **kwargs)

    @staticmethod
    def switch_realm(user, target_realm):
        """Authenticates the user into another realm.

        Args:
            user (dict): User representation of the authenticated user.
            target_realm (str): realms'd id of the target realm.
        """
        project = Project.objects.filter(instance_uri=target_realm).first()
        if project is None:
            return None
        keycloak_user = KeycloakUser.objects.filter(uuid=user["id"]).first()
        if keycloak_user is None:
            return None
        if keycloak_user.manager is None:
            return None
        users = KeycloakUser.objects.filter(manager=keycloak_user.manager)
        for user in users:
            if project.keycloak_realm == user.realm:
                realm = user.realm
                rc = RealmController(realm.realm, realm.admin, realm.password)
                token = rc.impersonate_user(user.uuid)
                return utils.encode_token(token)
        return None

    @staticmethod
    def update_credentials(user, target_id, **kwargs):
        keycloak_user = KeycloakUser.objects.filter(uuid=user["id"]).first()
        if keycloak_user is None or keycloak_user.realm is None:
            return None
        try:
            realm = keycloak_user.realm
            rc = RealmController(realm.realm, realm.admin, realm.password)
            rc.update_user_credentials(target_id, **kwargs)
            return True
        except Exception as e:
            Log.error("KeycloakUserModel.update_credentials", e)


class Project(mixin.Model, models.Model):
    """A Project represents a client instance

    Attributes:
        api_key: API key to access the customer server.
        api_secret: API secret to access the customer server.
        in_process: Whether the stack is being created (True) or not (False).
        instance_secret: Password of the instance "super user".
        instance_uri: Instance's URL.
        instance_username: username of the instance "super user".
        keycloak_realm: Keycloak realm used by the project.
        name: Name of the customer instance.
        owner (KeycloakUser): Owner.
    """

    api_key = models.CharField(max_length=254, null=True)
    api_secret = models.CharField(max_length=254, null=True)
    in_process = models.BooleanField(default=True)
    instance_secret = models.CharField(max_length=254, null=True)
    instance_uri = models.URLField(_("Instance URI"), max_length=128, unique=True)
    instance_username = models.CharField(max_length=254, null=True)
    keycloak_realm = models.ForeignKey(
        KeycloakRealm,
        related_name="project",
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
    )
    name = models.CharField(_("Project name"), max_length=128)
    owner = models.ForeignKey(
        KeycloakUser,
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
    )

    @property
    def status(self):
        stack = self.stack.first()
        if stack == None:
            return "unknown"
        if stack.status == Stack.Status.CANCELED:
            return "canceled"
        if stack.status == Stack.Status.ERROR:
            return "error"
        if stack.step == Stack.Step.END:
            return "online"
        return "creating"

    def __repr__(self):
        return f"<{self.name}: {self.instance_uri}>"

    def __str__(self):
        return self.__repr__()

    def get_random_alphanumeric_string(self, letters_count, digits_count):
        sample_str = "".join((random.choice(string.ascii_letters) for i in range(letters_count)))
        sample_str += "".join((random.choice(string.digits) for i in range(digits_count)))
        # Convert string to list and shuffle it to mix letters and digits
        sample_list = list(sample_str)
        random.shuffle(sample_list)
        final_string = "".join(sample_list)
        return final_string

    def invoke_super_access(self):
        """Creates a "super user" in the customer instance."""
        headers = {"content-type": "application/json"}
        object = {
            "jsonrpc": "2.0",
            "method": "invoke_super_access",
            "id": None,
            "params": [False, False, self.instance_username, self.instance_secret],
        }
        url = self.instance_uri + "/jsonrpc/1/instance/common"
        data = json.dumps(object)
        response = requests.post(url=url, headers=headers, data=data)
        if response.status_code == 200:
            result = response.json()["result"]
            return result
        return False

    @staticmethod
    def post_values(name, host):
        """Creates a new project. Projects can't be updated once created."""
        request = get_request()
        user_id = request.keycloak_user["id"]
        keycloak_user = KeycloakUser.objects.filter(uuid=user_id).first()
        if keycloak_user is None or keycloak_user.manager is None:
            return False
        manager = keycloak_user.manager
        if manager.main is None:
            return False
        project = Project.objects.create(instance_uri=host, name=name, owner=manager.main)
        Stack.create(project, host)
        return True

    def save(self, *args, **kwargs):
        parsed_uri = urlparse(self.instance_uri)
        self.instance_username = "instance@" + parsed_uri.netloc
        self.instance_secret = self.get_random_alphanumeric_string(12, 4)
        if not self.in_process:
            invoke_data = self.invoke_super_access()
            if not invoke_data:
                raise ValidationError("Unable to connect with remote instance.")
            self.api_key = invoke_data["api_key"]
            self.api_secret = invoke_data["api_secret"]
            self.setup()
        super(Project, self).save(*args, **kwargs)

    def serialize(self, *args, **kwargs):
        owner = None
        if self.owner:
            owner = str(self.owner.manager)
        return {
            "id": self.id,
            "instance_uri": self.instance_uri,
            "name": self.name,
            "owner": owner,
            "status": self.status,
        }

    def setup(self):
        """Finishes the setup of a customer instance"""
        headers = {"content-type": "application/json"}
        object = {
            "jsonrpc": "2.0",
            "method": "setup",
            "id": None,
            "params": [self.api_key, self.api_secret],
        }
        url = self.instance_uri + "/jsonrpc/1/instance/common"
        data = json.dumps(object)
        response = requests.post(url=url, headers=headers, data=data)
        if response.status_code == 200:
            result = response.json()["result"]
            return result
        return False


class Preference(models.Model):

    TYPE_INT = 1
    TYPE_STR = 2
    TYPE_BOOL = 3
    TYPE_FLOAT = 4
    TYPE_OBJECT = 5

    DATA_TYPE = (
        (TYPE_INT, _("Integer")),
        (TYPE_STR, _("String")),
        (TYPE_BOOL, _("Boolean")),
        (TYPE_FLOAT, _("Float")),
        (TYPE_OBJECT, _("Object")),
    )

    key = models.CharField(max_length=254)
    value = models.CharField(max_length=254)
    type = models.IntegerField(choices=DATA_TYPE)

    def save(self, *args, **kwargs):
        if not self.pk:
            super().save(*args, **kwargs)

    @staticmethod
    def put_value(key, value):
        if value is not None:
            db_pref, _ = Preference.objects.get_or_create(key=key)
            pref_type = Preference._get_preference_type(value)
            db_pref.type = pref_type
            db_pref.value = Preference._serialize_value(value, pref_type)
            db_pref.save()

    @staticmethod
    def get_value(key, default=False):
        obj = Preference.objects.filter(key=key).first()
        if obj and obj.value:
            return Preference._deserialize_value(obj.value, obj.type)
        return default

    @staticmethod
    def remove_value(key):
        obj = Preference.objects.filter(key=key).first()
        if obj:
            obj.delete()

    @staticmethod
    def _get_preference_type(value):
        if isinstance(value, int):
            return Preference.TYPE_INT
        elif isinstance(value, float):
            return Preference.TYPE_FLOAT
        elif isinstance(value, str):
            return Preference.TYPE_STR
        elif isinstance(value, bool):
            return Preference.TYPE_BOOL
        elif isinstance(value, (dict, list)):
            return Preference.TYPE_OBJECT
        else:
            raise ValueError(f"Unsupported preference value type: {type(value)}")

    @staticmethod
    def _serialize_value(value, pref_type):
        if pref_type == Preference.TYPE_OBJECT:
            return json.dumps(value)
        else:
            return str(value)

    @staticmethod
    def _deserialize_value(value, pref_type):
        if pref_type == Preference.TYPE_INT:
            return int(value)
        elif pref_type == Preference.TYPE_FLOAT:
            return float(value)
        elif pref_type == Preference.TYPE_STR:
            return str(value)
        elif pref_type == Preference.TYPE_BOOL:
            return bool(value)
        elif pref_type == Preference.TYPE_OBJECT:
            return json.loads(value)


class SkillStore(models.Model):

    STATE_DRAFT = 1
    STATE_VALIDATE = 2
    STATE_SUBMIT = 3
    STATE_APPROVED = 4
    STATE_PUBLISHED = 5
    STATE_REJECTED = 6
    STATE_REMOVED = 7

    STATE_SELECTIONS = (
        (STATE_DRAFT, _("Draft")),
        (STATE_VALIDATE, _("Validated")),
        (STATE_SUBMIT, _("Waiting for approval")),
        (STATE_APPROVED, _("Approved")),
        (STATE_PUBLISHED, _("Published")),
        (STATE_REJECTED, _("Rejected")),
        (STATE_REMOVED, _("Removed")),
    )

    CATEGORY_PRODUCTIVITY = 1

    CATEGORY_SELECTIONS = ((CATEGORY_PRODUCTIVITY, _("Productivity")),)

    name = models.CharField(max_length=128)
    summary = models.CharField(max_length=254)
    package = models.CharField(max_length=254)
    component = models.CharField(max_length=254, null=True)
    category = models.TextField(max_length=128)
    description = models.TextField()
    state = models.IntegerField(choices=STATE_SELECTIONS, default=STATE_DRAFT)
    reject_reason = models.TextField(null=True)
    data = models.TextField()

    def __str__(self):
        return self.name


class Stack(models.Model):
    """This class asynchronously creates and setups customers stack. A stack includes a keycloak
    realm, a gitlab pipeline and project, and a django server.

    Attributes:
        data (str): JSON string with stack data.
        project: Project linked to the stack.
        status (int): Status of the current step in the stack creation.
        step (int): Current step of the stack creation.
    """

    class Status(models.IntegerChoices):
        PENDING = 0
        RUNNING = 1
        FINISHED = 2
        ERROR = 3
        CANCELED = 4

        @staticmethod
        def get_label(value):
            for item in list(Stack.Status):
                if item.value == value:
                    return item.label

    class Step(models.IntegerChoices):
        KEYCLOAK = 0
        GITLAB = 1
        SETUP = 2
        END = 3

        @staticmethod
        def get_label(value):
            for item in list(Stack.Step):
                if item.value == value:
                    return item.label

    data = models.TextField(default="{}")
    project = models.ForeignKey(Project, related_name="stack", on_delete=models.CASCADE)
    status = models.IntegerField(choices=Status.choices, default=Status.PENDING)
    step = models.IntegerField(choices=Step.choices, default=Step.KEYCLOAK)

    def __repr__(self):
        return f"<Stack ({self.project.name}): {Stack.Step.get_label(self.step)} -> {Stack.Status.get_label(self.status)}>"

    def __str__(self):
        return self.__repr__()

    @staticmethod
    def _create(project, host):
        host_production, host_staging = Stack._get_hosts(host)
        random_id = get_random_string(5, "0123456789abcdefghijklmnopqrstuvwxyz")
        stack = Stack.objects.create(
            data=json.dumps(
                {
                    "host_production": host_production,
                    "host_staging": host_staging,
                    "random_id": random_id,
                }
            ),
            project=project,
            status=Stack.Status.PENDING,
            step=Stack.Step.KEYCLOAK,
        )
        stack.next()

    @staticmethod
    def _generate_secrets(**kwargs):
        """Creates a SECRET_KEY and SECRET_TOKEN for use in a customer instance.

        Args:
            kwargs: Extra data to append in the token.

        Returns:
            tuple[str, str]: A tuple with the SECRET_KEY and SECRET_TOKEN. The token is a JWT with
                expiration of 1 day.
        """
        exp = datetime.datetime.utcnow() + datetime.timedelta(days=1)
        secret = get_random_string(
            50, f"{string.digits}{string.ascii_letters}!#$%&()*+-<=>?@[]^_|~"
        )
        token = jwt.encode({**kwargs, "exp": exp}, secret)
        return secret, token

    @staticmethod
    def _get_hosts(host):
        parsed_url = urlparse(host)
        production_host = parsed_url.netloc
        staging_host = f"staging-{production_host}"
        return production_host, staging_host

    @staticmethod
    def _rerun(stack, step):
        stack.clear_data("error")
        stack.clear_data("setup_tries")
        stack.set_step(step)
        stack.next()

    @staticmethod
    def _resume(stack):
        stack.next()

    def cancel(self):
        if self.status != Stack.Status.ERROR or self.step != Stack.Step.END:
            self.set_status(Stack.Status.CANCELED)

    def check_pipeline(self):
        gl = gitlab.Gitlab("https://gitlab.com", private_token=settings.GITLAB["ACCESS_TOKEN"])
        project = gl.projects.get(settings.GITLAB["CREATE_PIPELINE_ID"])
        pipeline = project.pipelines.get(self.get_data("pipeline_id"))

        if pipeline.status == "success":
            self.set_status(Stack.Status.FINISHED)
        elif pipeline.status in ["canceled", "failed", "skipped", "unknown"]:
            self.set_error(f"Gitlab pipeline failed: {pipeline.status}")
        else:
            Log.info(
                f"Stack <{self.project.name}>",
                f"Gitlab pipeline {pipeline.id} is still running",
            )
            time.sleep(60)

    def check_realm(self):
        """ """
        valid = self.project.keycloak_realm.check_status()
        if valid:
            self.project.keycloak_realm.clone_user(self.project.owner.manager)
            self.set_status(Stack.Status.FINISHED)

    def check_server(self):
        pass

    def clear_data(self, key):
        data = json.loads(self.data)
        if key in data:
            del data[key]
            self.data = json.dumps(data)
            self.save()

    @staticmethod
    def create(project, host):
        """Asyncronously creates a new project stack

        Args:
            project: Project linked to the stack
            host: URL for the customer server.

        Returns:
            The thread created to process the pipeline.
        """
        thread = threading.Thread(target=Stack._create, args=[project, host])
        thread.start()
        return thread

    def create_pipeline(self):
        """Triggers the creation of a client stack with gilab. Customer stacks can only be deleted
        manually by a gitlab manager.

        Args:
            host (str):
            random_id (str):
        """
        # TODO (cuauh): Use oauth_token
        secret, token = Stack._generate_secrets()
        gl = gitlab.Gitlab("https://gitlab.com", private_token=settings.GITLAB["ACCESS_TOKEN"])
        project = gl.projects.get(settings.GITLAB["CREATE_PIPELINE_ID"])
        pipeline = project.pipelines.create(
            {
                "ref": settings.GITLAB["REF_BRANCH"],
                "variables": [
                    {
                        "key": "KEYCLOAK_ADMIN_PASSWORD",
                        "value": self.project.keycloak_realm.password,
                    },
                    {
                        "key": "KEYCLOAK_ADMIN_USERNAME",
                        "value": self.project.keycloak_realm.admin,
                    },
                    {"key": "KEYCLOAK_CLIENT_ID", "value": "internal-realm-admin"},
                    {
                        "key": "KEYCLOAK_REALM",
                        "value": self.project.keycloak_realm.realm,
                    },
                    {"key": "PRODUCTION_HOSTNAME", "value": self.get_data("host_production")},
                    {"key": "STAGING_HOSTNAME", "value": self.get_data("host_staging")},
                    {"key": "RANDOM_NUMBER", "value": self.get_data("random_id")},
                    {"key": "SECRET_KEY", "value": secret},
                    {"key": "SECRET_TOKEN", "value": token},
                ],
            }
        )

        self.set_data("pipeline_id", pipeline.id)
        self.set_data("token", token)
        self.set_status(Stack.Status.RUNNING)

    def create_realm(self):
        """Creates a Keycloak realm for the instance"""
        self.set_status(Stack.Status.RUNNING)

        # TODO (cuauh): Check for deployment error

        try:
            realm = KeycloakRealm.create(self.get_data("host_production").replace(".", "-"))
            if realm:
                self.project.keycloak_realm = realm
                self.project.save()
            else:
                self.set_error("Error creating keycloak server")
        except Exception as e:
            self.set_error(str(e))

    def get_data(self, key, default=None):
        data = json.loads(self.data)
        try:
            return data[key]
        except:
            return default

    def next(self, step=True):
        """Checks the status of the current step and if it is finished moves the the next one.

        Args:
            step (bool): If True call next again at the end of the method. Defaults to True
        """
        if (
            self.status == Stack.Status.CANCELED
            or self.status == Stack.Status.ERROR
            or self.step == Stack.Step.END
        ):
            return

        if self.step == Stack.Step.KEYCLOAK:
            if self.status == Stack.Status.PENDING:
                self.create_realm()
            elif self.status == Stack.Status.RUNNING:
                self.check_realm()
            elif self.status == Stack.Status.FINISHED:
                self.set_step(Stack.Step.GITLAB)

        elif self.step == Stack.Step.GITLAB:
            if self.status == Stack.Status.PENDING:
                self.create_pipeline()
            elif self.status == Stack.Status.RUNNING:
                self.check_pipeline()
            elif self.status == Stack.Status.FINISHED:
                self.set_step(Stack.Step.SETUP)

        elif self.step == Stack.Step.SETUP:
            if self.status == Stack.Status.PENDING:
                self.setup_server()
            elif self.status == Stack.Status.RUNNING:
                self.check_server()
            elif self.status == Stack.Status.FINISHED:
                self.set_step(Stack.Step.END)

        if step:
            time.sleep(10)
            self.next()

    @staticmethod
    def rerun(stack, step=Step.SETUP):
        """Reruns stack step, any following step will also be reran.

        Args:
            stack: Stack instance.
            step: From which step start. Defaults to Stack.Step.SETUP.
        """
        thread = threading.Thread(target=Stack._rerun, args=[stack, step])
        thread.start()
        return thread

    @staticmethod
    def resume(stack):
        """Resumes a pending stack"""
        thread = threading.Thread(target=Stack._resume, args=[stack])
        thread.start()
        return thread

    def set_data(self, key, value):
        data = json.loads(self.data)
        data[key] = value
        self.data = json.dumps(data)
        self.save()

    def set_error(self, message):
        self.status = Stack.Status.ERROR
        self.set_data("error", message)
        Log.error(
            f"Stack <{self.project.name}>",
            Stack.Step.get_label(self.step),
            Stack.Status.get_label(self.status),
            message,
        )

    def set_status(self, status):
        self.status = status
        self.save()
        Log.info(
            f"Stack <{self.project.name}>",
            f"{Stack.Step.get_label(self.step)} {Stack.Status.get_label(self.status)}",
        )

    def set_step(self, step):
        self.status = Stack.Status.PENDING
        self.step = step
        self.save()
        Log.info(
            f"Stack <{self.project.name}>",
            f"{Stack.Step.get_label(self.step)} {Stack.Status.get_label(self.status)}",
        )

    def setup_server(self):
        try:
            self.project.in_process = False
            self.project.save()
            self.set_status(Stack.Status.FINISHED)
        except Exception as e:
            # pipeline shouldn't take more than one hour to finish
            tries = self.get_data("setup_tries", 1)
            if tries > 60:
                self.set_error(str(e))
            else:
                self.set_data("setup_tries", tries + 1)
                time.sleep(60)
