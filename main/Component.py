import abc
import base64
import json
import os
import urllib.parse as urlparse
import cryptocode
from django.conf import settings
from jinja2 import Template
from requests_oauthlib import OAuth2Session

from . import Log
from .Block import get_block_by_property

CYPHER_KEY = "D619C875B93FB"

def merge_params(url, params):
    url_parts = list(urlparse.urlparse(url))
    query = dict(urlparse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urlencode(query)
    return urlparse.urlunparse(url_parts)

def parse_params(authorization_response, **kwargs):
    parsed = urlparse.urlparse(authorization_response)
    simple_dict = {}
    for k, v in urlparse.parse_qs(parsed.query).items():
        simple_dict[k] = v[0]
    return simple_dict

def state_from_response(authorization_response, **kwargs):
    state_encoded = parse_params(authorization_response)["state"]
    state_str = base64.b64decode(state_encoded).decode()
    decoded = cryptocode.decrypt(state_str, CYPHER_KEY)
    state = json.loads(decoded)
    return state

def state_to_string(state):
    state_str = json.dumps(state)
    encoded = cryptocode.encrypt(state_str, CYPHER_KEY)
    state = base64.b64encode(bytes(encoded, "utf-8")).decode()
    return state

def user_id_from_state(state):
    return state["user_id"]

class BaseComponent(ABC):
    def __init__(self, config):
        self._name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        self._config = config
        self._meta = {}
        if not config:
            Log.warning("BaseComponent", f"config is empty or none within {self._name}")

    def get_config(self):
        return self._config

    def get_name(self):
        return self._name

    def get_variable(self, component, key):
        """
        Args:
            component (str): Integration's identifier.
            key (str): Name of the variable.

        Returns:
            Variable's value if it exists, None otherwise.

        Example:
            self.get_variable("com.bigitsystems", "FETCH_UNPUBLISHED")
        """
        pass

    def update_meta(self, meta):
        self._meta.update(meta)

    def get_meta(self):
        return self._meta

    def get_file_content(self, path):
        """
        Reads the content of the file located at the specified path.

        Args:
            path (str): Path to the file relative to the directory of the current module.

        Returns:
            The contents of the file.
        """
        file_dir = os.path.dirname(self.__module__.replace(".", "/"))
        target_file = os.path.join(file_dir, path)
        if os.path.exists(target_file):
            with open(target_file, "r") as f:
                return f.read()


class ChatProvider(BaseComponent):
    def can_process(self, binder, statement, *args, **kwargs):
        return False

    def on_match_object(self, binder, statement, *args, **kwargs):
        return 0.0, None

    def process(self, binder, statement, threshold, match_object, *args, **kwargs):
        pass


class OAuthProvider(BaseComponent):
    @abc.abstractmethod
    def authorization_url(self, redirect_uri, user_id, **kwargs):
        """Return the authorization url. This method must be overridden."""
        pass

    def authenticate(self, binder, user_id, **kwargs):
        """Authenticates an existing OAuth token.

        Returns the OAuth session object if the token is still valid, None otherwise.
        """
        token = self.load_token(binder, user_id, **kwargs)
        if token:
            if self.is_expired(user_id, token, **kwargs):
                token = self.refresh_token(user_id, token, **kwargs)
                self.save_token(binder, user_id, token, **kwargs)

            oauth = self.build_oauth(token, **kwargs)
            if self.is_authorized(oauth, **kwargs):
                return oauth

        return None

    def build_oauth(self, token, **kwargs):
        """Return a new OAuth session object. Override this method if necessary."""
        oauth = OAuth2Session(token=token)
        return oauth

    def get_authorization_url(self, binder, user_id, **kwargs):
        state = binder.on_load_state()
        trim_state = {
            "component_name": self.get_name(),
            "channel_id": state.channel_id,
            "user_id": state.user_id,
            "operator_id": state.operator_id,
        }
        auth_url = self.authorization_url(self.get_redirect_uri(binder), user_id)
        state_string = state_to_string(trim_state)
        final_url = merge_params(auth_url, {"state": state_string})
        return final_url

    def get_redirect_uri(self, binder):
        return binder.oauth_redirect_url

    @abc.abstractmethod
    def fetch_token(self, redirect_uri, authorization_response, **kwargs):
        """Fetch authorization token. This method must be overridden."""
        pass

    @abc.abstractmethod
    def is_expired(self, user_id, token, **kwargs):
        pass

    def is_authorized(self, oauth, **kwargs):
        """Checks if the OAuth session is valid. This method should be overridden."""
        return True

    def load_token(self, binder, user_id, **kwargs):
        return binder.on_load_oauth_token(self.get_name(), user_id)

    def on_redirect(self, binder, authorization_response, **kwargs):
        try:
            state = state_from_response(authorization_response, **kwargs)
            redirect_uri = self.get_redirect_uri(binder)
            token = self.fetch_token(redirect_uri, authorization_response, **kwargs)
            user_id = user_id_from_state(state)
            if user_id:
                self.save_token(binder, user_id, token, **kwargs)
                return True
        except:
            # invalid OAuth redirect
            pass

        return False

    @abc.abstractmethod
    def refresh_token(self, user_id, token, **kwargs):
        """Refresh authorization token."""
        pass

    def save_token(self, binder, user_id, token, **kwargs):
        binder.on_save_oauth_token(self.get_name(), user_id, token)

class PaymentProvider(BaseComponent):

    @abc.abstractmethod
    def build_payment_page(self, binder, state, *args, **kwargs):
        """Builds a payment page. This method must be overridden."""
        pass

    @abc.abstractmethod
    def make_payment(self, binder, state, params, *args, **kwargs):
        """Makes a payment. This method must be overridden."""
        pass

    def render(self, template, state, data=None):
        """Renders a template with state data and returns the resulting HTML."""
        print("static =>", settings.STATIC_URL)
        template_data = {
            "__amount__": state["amount"],
            "__component__": self.get_name(),
            "__state__": state_to_string(state),
            "__static__": settings.STATIC_URL,
        }
        if data:
            template_data.update(data)

        content = self.get_file_content(template)
        html = Template(content).render(template_data)
        return html

    def get_redirect_uri(self, binder):
        """Returns the redirect URI for payment processing."""
        return binder.payment_redirect_url

    def on_redirect(self, binder, authorization_response, **kwargs):
        """Converts the callback to a payment reference."""
        try:
            state = state_from_response(authorization_response, **kwargs)
            redirect_uri = self.get_redirect_uri(binder)
            params = parse_params(authorization_response, **kwargs)
            user_id = user_id_from_state(state)
            if user_id:
                payed = self.make_payment(binder, state, params)
                if payed:
                    return True
        except:
            # Invalid payment redirect
            pass
        return False

    def get_payment_url(self, binder, user_id, amount, currency, **kwargs):
        """Returns the URL for payment processing."""
        state = binder.on_load_state()
        trim_state = {
            "component_name": self.get_name(),
            "channel_id": state.channel_id,
            "user_id": state.user_id,
            "operator_id": state.operator_id,
            "amount": amount,
            "currency_code": currency,
        }
        state_string = state_to_string(trim_state)
        final_url = merge_params(binder.html_render_url, {"state": state_string})
        return final_url


class SkillProvider(BaseComponent):
    @abc.abstractmethod
    def on_execute(self, binder, user_id, package, data, *args, **kwargs):
        """Process skill. This method must be overridden.

        When the skill is processed successfully, the method should return data that is going to be
        mixed with the Nodes defined in the property nodes of the skill block.

        Args:
            binder (main.Binder.Binder)
            user_id (int): Id of user interacting with the skill
            package (str): Package identifier, e.g. "com.bits.wordpress.skill"
            data (dict): Skill state
            args (list): Contains a main.Statement.InputStatement if processor is managed by
                main.Block.InputSkill
            kwargs (dict): Extra arguments, the complete skill definition is passed here as
                {"skill": {skill_definition...}}.

        Returns:
            - False or None: If skill couldn't be processed.
            - Other: Depends on the nodes defined in the block.
        """
        pass

    @abc.abstractmethod
    def on_search(self, binder, user_id, package, searchable, query, **kwargs):
        """Returns a list of suggestions based on a user query. This method must be overridden.

        This method is only called when the skill provider is wrapped in main.Block.InputSkill.

        Args:
            binder (main.Binder.Binder)
            user_id (int): Id of user interacting with the skill
            package (str): Package identifier, e.g. "com.bits.wordpress.skill"
            searchable (bool): True if the skill is searchable, otherwise False.
            query (str): User query
            kwargs (dict): Extra arguments, the complete skill definition is passed here as
                {"skill": {skill_definition...}}.

        Returns:
            list: A list of main.Node.SearchNode. Build the results with the static method
                SearchNode.wrap_text(human_readable_value, value) where human_readable_value is a
                string, and value can be any type. human_readable_value and value will be passed in
                a main.Statement.InputStatement as text and input respectively.
        """
        pass

    def on_query_search(self, binder, user_id, package, data, query, **kwargs):
        """Returns the best possible search input value against a query"""
        pass

    def on_verify_input(self, binder, user_id, package, searchable, value, **kwargs):
        """Verify search input"""
        return True

    def oauth(self, binder, user_id, component, **kwargs):
        real_user_id = binder.on_load_state().user_id
        skill = binder.on_load_state().skill
        block = get_block_by_property(
            binder, skill, "component", component.__module__ + "." + component.__name__
        )
        return block.oauth(binder, real_user_id)
