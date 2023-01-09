"""This module contains extra functions not available in the customer repo. The following functions were added:

- get_blocks
- validate_skill
"""

import abc
from abc import ABC, abstractmethod
import json
import base64
from deprecated import deprecated
import urllib.parse as urlparse

from contrib.exceptions import JsonRPCException

from . import Flag, Log
from .Component import PaymentProvider, state_from_response, user_id_from_state
from .Flag import FlagManager
from .Processor import StartSkill, CancelSkill, StandardInput, SkillProcessor
from .Statement import InputStatement
from .Block import (
    get_block_by_id,
    DataExchange,
    DecisionBlock,
    InputDate,
    InputDateTime,
    InputDuration,
    InputEmail,
    InputFile,
    InputNumber,
    InputOAuth,
    InputPayment,
    InputSearchable,
    InputSelection,
    InputSkill,
    InputText,
    InterpreterSkill,
    PromptBinary,
    PromptChatPlatform,
    PromptDate,
    PromptDateTime,
    PromptDuration,
    PromptPayment,
    PromptPreview,
    PromptImage,
    PromptText,
    TerminalBlock,
)


DATA_EXCHANGE = [DataExchange]
INPUT_BLOCKS = [
    DecisionBlock,
    InputDate,
    InputDateTime,
    InputDuration,
    InputEmail,
    InputFile,
    InputNumber,
    InputOAuth,
    InputPayment,
    InputSearchable,
    InputSelection,
    InputSkill,
    InputText,
]
INTERPRETER_BLOCKS = [InterpreterSkill]
OTHER_BLOCKS = [TerminalBlock]
PROMPT_BLOCKS = [
    PromptBinary,
    PromptChatPlatform,
    PromptDate,
    PromptDateTime,
    PromptDuration,
    PromptImage,
    PromptPayment,
    PromptPreview,
    PromptText,
]


def _get_block_names(block_classes):
    data = []
    for item in block_classes:
        data.append(item.__module__ + "." + item.__name__)
    return data


def get_blocks():
    data = []
    reg = Registry()
    for block in reg.blocks:
        block_object = block(None, None, None, None)
        data.append(block_object.serialize())
    return data


def get_component(query, filter):
    data = []
    reg = Registry()
    for item in reg.components:
        data.append([item.get_name(), item.__name__])
    return data


def get_connections(component_name, properties):
    reg = Registry()
    for block in reg.blocks:
        if block.__module__ + "." + block.__name__ == component_name:
            block_object = block(None, None, None, None)
            return block_object.get_connections(properties)
    return None


def validate_skill(skill):
    """Validates a skill

    Args:
        skill (dict): The skill definitions. Must have the following fields:
            - name (str): Skill's name.
            - package (str): Skill's identifier, e.g. "com.bits.wordpress"
            - start (str): Id of the starting block, e.g. "ihqt"
            - blocks (list): Skill blocks.
    """
    try:
        start_id = skill["start"]
    except:
        raise JsonRPCException("skill must have a field 'start'")
    try:
        blocks = skill["blocks"]
    except:
        raise JsonRPCException("skill must have a field 'blocks'")

    has_terminal_end = False
    for item in blocks:
        if item["id"] == start_id:
            if item["component"] not in _get_block_names(INPUT_BLOCKS):
                break
            raise JsonRPCException("Start block should not be InputBlock")

    for item in blocks:
        if item["component"] in _get_block_names([TerminalBlock]):
            has_terminal_end = True
            break

    if not has_terminal_end:
        raise JsonRPCException("Skill has no TerminalBlock")

    return True


class Registry:
    def __init__(self):
        self.blocks = []
        self.components = []

        self.blocks.extend(PROMPT_BLOCKS)
        self.blocks.extend(INPUT_BLOCKS)
        self.blocks.extend(INTERPRETER_BLOCKS)
        self.blocks.extend(DATA_EXCHANGE)
        self.blocks.extend(OTHER_BLOCKS)

    def register(self, object):
        self.components.append(object)
        pass

    def get_component(self, binder, component_name):
        for item in self.components:
            item_name = item.__module__ + "." + item.__name__
            if item_name == component_name:
                config = binder.on_get_component_config(item_name)
                return item(config)

    def payment_providers(self, binder):
        array_list = []
        for item in self.components:
            item_name = item.__module__ + "." + item.__name__
            config = binder.on_get_component_config(item_name)
            object = item(config)
            if isinstance(object, PaymentProvider):
                array_list.append(object)
        return array_list


class Binder(ABC):
    def __init__(self, registry, **kwargs):
        self.registry = registry
        self.oauth_redirect_url = kwargs.get("OAUTH_REDIRECT_URL")
        self.payment_redirect_url = kwargs.get("PAYMENT_REDIRECT_URL")
        self.html_render_url = kwargs.get("HTML_RENDER_URL")

        pass

    # this method should return oauth token against component for user_id
    @abc.abstractmethod
    def on_load_oauth_token(self, component, user_id):
        pass

    # this method should save oauth token against component for user_id
    @abc.abstractmethod
    def on_save_oauth_token(self, component, user_id, token):
        pass

    # context of user bot channel
    @abc.abstractmethod
    def on_context(self):
        pass

    @abc.abstractmethod
    def on_get_component_config(self, component):
        pass

    @abc.abstractmethod
    def on_standard_input(self, input, output):
        pass

    # should post message to the channel
    @abc.abstractmethod
    def on_post_message(self, statement):
        pass

    @abc.abstractmethod
    def on_load_state(self):
        pass

    @abc.abstractmethod
    def on_save_state(self, state_json):
        pass

    # should return json
    @abc.abstractmethod
    def on_get_skill(self, package):
        pass

    @abc.abstractmethod
    def on_cancel_intent(self, statement):
        pass

    @abc.abstractmethod
    def on_skill_intent(self, statement):
        pass

    # send new message
    def post_message(self, statement):
        self.on_post_message(statement)

    def search_query(self, query=None):
        state = self.on_load_state()
        if state.is_active():
            user_id = state.user_id
            client = get_block_by_id(self, state.skill, state.block_id)
            items = client.on_search(self, user_id, query)
            return items
        else:
            pass
        return []

    @deprecated(version="1.0.0", reason="You should use notify_request function")
    def notify_oauth_redirect(self, authorization_response, **kwargs):
        return self.notify_request(authorization_response, **kwargs)

    def notify_request(self, authorization_response, **kwargs):
        state = state_from_response(authorization_response, **kwargs)
        user_id = user_id_from_state(state)
        if user_id:
            input_input = authorization_response
            input_flag = Flag.FLAG_STANDARD_INPUT
            input = InputStatement(user_id, input=input_input, flag=input_flag)
            self.select_processor(input)

    # get registry
    def get_registry(self):
        return self.registry

    def select_processor(self, input):
        if input.text:
            Log.message("Message", input.text, True)
        # get flag from input
        flag_manager = FlagManager()
        statement, flag = flag_manager.load(self, input)
        Log.debug("Flag Detection", flag)
        Log.debug("Statement", statement)

        # based on flag select processor
        if flag == Flag.FLAG_START_SKILL:
            StartSkill().on_process(self, statement)
        elif flag == Flag.FLAG_SKILL_PROCESSOR:
            SkillProcessor().on_process(self, statement)
        elif flag == Flag.FLAG_CANCEL_SKILL:
            CancelSkill().on_process(self, statement)
        else:
            StandardInput().on_process(self, statement)
