"""This module can't import the following models from teh instance repo:

- AppData
"""

import abc
from abc import ABC, abstractmethod
import base64
import inspect
import os
import urllib.parse as urlparse
from urllib.parse import urlencode

import cryptocode
from django.conf import settings
from jinja2 import Template
import json
from requests_oauthlib import OAuth2Session

from . import Log
from .Block import get_block_by_property

# TODO: must use dynamic one
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
        self._name = self.__class__.__module__ + "." + self.__class__.__name__
        self._config = config
        self._meta = {}
        if not config:
            Log.warning("BaseComponent", "config is empty or none within " + self._name)

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

    # this method reads file content from siblings path
    def get_file_content(self, path):
        # curr_file = inspect.getfile(inspect.currentframe())
        # file_dir = os.path.dirname(os.path.abspath(curr_file))
        # target_file = os.path.join(file_dir, path)
        file_dir = os.path.dirname(self.__module__.replace(".", "/"))
        target_file = os.path.join(file_dir, path)
        if os.path.exists(target_file):
            f = open(target_file, "r")
            return f.read()


class ChatProvider(BaseComponent):
    def can_process(self, binder, statement, *args, **kwargs):
        return False

    def on_match_object(self, binder, statement, *args, **kwargs):
        return 0.0, None

    def process(self, binder, statement, threshold, match_object, *args, **kwargs):
        pass


class OAuthProvider(BaseComponent):
    def authenticate(self, binder, user_id, **kwargs):
        """Authenticates an existing oauth token.

        Returns the oauth session object if the token is still valid, None otherwise.
        """
        token = self.load_token(binder, user_id, **kwargs)

        if token:
            expired = self.is_expired(user_id, token, **kwargs)
            if expired:
                token = self.refresh_token(user_id, token, **kwargs)
                self.save_token(binder, user_id, token, **kwargs)
            # create OAuth2Session using latest token
            oauth = self.build_oauth(token, **kwargs)
            # make sure it is valid against latest scope
            authorized = self.is_authorized(oauth, **kwargs)
            if authorized:
                # return un expired authorized scope token
                return oauth
        return None

    @abc.abstractmethod
    def authorization_url(self, redirect_uri, user_id, **kwargs):
        """Return the authorization url. This method must be overrided."""
        pass

    def build_oauth(self, token, **kwargs):
        """Return a new oauth session object. Override this method if neccessary"""
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
        """Fetch authorization token. This method must be overrided"""
        pass

    def is_authorized(self, oauth, **kwargs):
        """Checks if the oauth session is valid. This method should be overrided"""
        return True

    @abc.abstractmethod
    def is_expired(self, user_id, token, **kwargs):
        pass

    def load_token(self, binder, user_id, **kwargs):
        return binder.on_load_oauth_token(self.get_name(), user_id)

    # this method convert incoming callback to oauth token
    def on_redirect(self, binder, authorization_response, **kwargs):
        try:
            state = state_from_response(authorization_response, **kwargs)
            redirect_uri = self.get_redirect_uri(binder)
            token = self.fetch_token(redirect_uri, authorization_response, **kwargs)
            user_id = user_id_from_state(state)
            if user_id:
                self.save_token(binder, user_id, token)
                return True
        except:
            # invalid oauth redirect
            pass
        return False

    @abc.abstractmethod
    def refresh_token(self, user_id, token, **kwargs):
        """Refresh authorization token"""
        pass

    def save_token(self, binder, user_id, token, **kwargs):
        binder.on_save_oauth_token(self.get_name(), user_id, token)

    # def simple_fetch_token(self, redirect_uri, authorization_response, url, **kwargs):
    #     scope = kwargs.get('scope',[])
    #     client_id = self.get_config().get('client_id')
    #     client_secret = self.get_config().get('client_secret')
    #     oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
    #     return oauth.fetch_token(url,authorization_response=authorization_response,
    #                                   client_secret=client_secret)

    # @staticmethod
    # def notify_redirect(binder, authorization_response, **kwargs):
    #     parsed = urlparse.urlparse(authorization_response)
    #     state_encoded = urlparse.parse_qs(parsed.query)['state'][0]
    #     state_str = base64.b64decode(state_encoded).decode()
    #     state = json.loads(state_str)
    #     component_name = state['component_name']
    #     component_object = binder.get_registry().get_component(binder, component_name)
    #     on_redirect = component_object.on_redirect(binder, authorization_response, **kwargs)
    #     return on_redirect


class PaymentProvider(BaseComponent):

    # this method returns html
    @abc.abstractmethod
    def build_payment_page(self, binder, state, *args, **kwargs):
        pass

    @abc.abstractmethod
    def make_payment(self, binder, state, params, *args, **kwargs):
        pass

    def render(self, template, state, data=None):
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
        return binder.payment_redirect_url

    # this method convert incoming callback to payment reference
    def on_redirect(self, binder, authorization_response, **kwargs):
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
            # invalid oauth redirect
            pass
        return False

    def get_payment_url(self, binder, user_id, amount, currency, **kwargs):
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
    def oauth(self, binder, user_id, component, **kwargs):
        real_user_id = binder.on_load_state().user_id
        skill = binder.on_load_state().skill
        block = get_block_by_property(
            binder, skill, "component", component.__module__ + "." + component.__name__
        )
        return block.oauth(binder, real_user_id)

    @abc.abstractmethod
    def on_execute(self, binder, user_id, package, data, *args, **kwargs):
        """Process skill. This method must be overrided.

        When the skill is processed succesfully the method shoudl return data that is going to be
        mixed with the Nodes defined in the property nodes of the skill block.

        Args:
            binder (main.Binder.Binder)
            user_id (int): Id of user interacting with the skill
            package (str): Package indetifier, e.g. "com.bits.wordpress.skill"
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

    # this method should return best possible search input value against query
    def on_query_search(self, binder, user_id, package, data, query, **kwargs):
        """ """
        pass

    # this method returns list of search result against query
    @abc.abstractmethod
    def on_search(self, binder, user_id, package, searchable, query, **kwargs):
        """Returns a list of suggestions based on a user query. This method must be overrided.

        This method is only called when the skill provider is wrapped in main.Block.InputSkill.

        Args:
            binder (main.Binder.Binder)
            user_id (int): Id of user interacting with the skill
            package (str): Package indetifier, e.g. "com.bits.wordpress.skill"
            data (dict): Skill state
            query (str): User query
            kwargs (dict): Extra arguments, the complete skill definition is passed here as
                {"skill": {skill_definition...}}.

        Returns:
            list: A list of main.Node.SearchNode. Build the results with the static method
                SearchNode.wrap_text(human_readeable_value, value) where human_readeable_value is a
                string, and value can be any type. human_redeable_value and value will be passed in
                a main.Statement.InputStatement as text and input respectevely.
        """
        pass

    def on_verify_input(self, binder, user_id, package, searchable, value, **kwargs):
        """Verify search input"""
        return True
