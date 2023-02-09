"""This module must be a perfect copy of the equivalent module in the the customer template repository in multi-tenant deployments."""

from abc import ABC, abstractmethod
import datetime
import random
import re

from durations import Duration
from jinja2 import Template

from .Log import Log
from .Node import (
    BinaryNode,
    DateNode,
    DateTimeNode,
    DurationNode,
    IFrameNode,
    ImageNode,
    InputFileNode,
    OAuthNode,
    PaymentNode,
    PreviewNode,
    SearchNode,
)
from .Statement import OutputStatement
from .Utils import Utils


BLOCK_REJECT = -1
BLOCK_ACCEPT = 0
BLOCK_MOVE = 1
BLOCK_MOVE_X = 2
BLOCK_MOVE_Y = 3
BLOCK_MOVE_Z = 4


def get_block_by_id(binder, skill, block_id):
    block_data = next((item for item in skill["blocks"] if item["id"] == block_id), None)
    if block_data is None:
        raise ValueError(f"Block not found for id: {block_id}")
    component = block_data["component"]
    block = next((b for b in binder.get_registry().blocks if component == f"{b.__module__}.{b.__name__}"), None)
    if block is None:
        raise ValueError(f"Component not found for id: {block_id}")
    connections = block_data.get("connections")
    return block(binder.on_context(), block_data["id"], block_data["properties"], connections)


def get_block_by_property(binder, skill, key_name, key_value):
    match = next((item for item in skill["blocks"] 
                  if item["component"] in (f"{b.__module__}.{b.__name__}" for b in binder.get_registry().blocks)
                  and block_obj:=block(binder.on_context(), item["id"], item["properties"], item.get("connections"))
                  and block_obj.property_value(key_name) == key_value), None)
    if match is None:
        raise ValueError(f"Block not found for property {key_name} with value {key_value}")
    return block_obj


class BlockResult:
    def __init__(self, block, code, connection):
        self.block = block
        self.code = code
        self.connection = connection

    @classmethod
    def status(cls, block, code, connection):
        return cls(block, code, connection)

    def is_rejected(self):
        return self.code == BLOCK_REJECT

    def post_skill(self):
        if isinstance(self.block, TerminalBlock):
            return self.block.post_skill()


class BaseBlock(ABC):
    def __init__(self, context, id, properties, connections):
        self.component = self.__class__.__module__ + "." + self.__class__.__name__
        self.context = context
        self.id = id
        self.properties = properties
        self.connections = connections
        self.template_properties = []
        self.load_template()
        # should call after load template
        self.on_init()

    # use this method as constructor
    def on_init(self):
        """Initialize the block with default values"""
        pass

    def get_meta(self) -> dict:
        """Return the meta data"""
        return self.meta

    def serialize(self):
        return {
            "component": self.component,
            "descriptor": self.on_descriptor(),
            "template": self.template_properties,
            "connections": self.get_connections(self.properties),
        }

    def property_value(self, key: str) -> Union[str, int, float, dict]:
        """Return the value of the property with the given key"""
        for item in self.properties:
            name = item["name"]
            value = item["value"]
            if name == key:
                return value

    def find_connection(self, code):
        if self.connections:
            for item in self.connections:
                if item[0] == code:
                    return item[1]

    def move(self):
        return BlockResult.status(self, BLOCK_MOVE, self.find_connection(BLOCK_MOVE))

    def move_x(self):
        return BlockResult.status(self, BLOCK_MOVE_X, self.find_connection(BLOCK_MOVE_X))

    def move_y(self):
        return BlockResult.status(self, BLOCK_MOVE_Y, self.find_connection(BLOCK_MOVE_Y))

    def move_z(self):
        return BlockResult.status(self, BLOCK_MOVE_Z, self.find_connection(BLOCK_MOVE_Z))

    def accept(self):
        return BlockResult.status(self, BLOCK_ACCEPT, self.find_connection(BLOCK_ACCEPT))

    def reject(self):
        return BlockResult.status(self, BLOCK_REJECT, self.find_connection(BLOCK_REJECT))

    # this method for defining block properties
    def load_template(self):
        pass

    @abstractmethod
    def on_descriptor(self):
        pass

    def append_template_properties(self, properties):
        self.template_properties.extend(properties)

    def remove_template_properties(self, name):
        self.template_properties[:] = [item for item in self.template_properties if item["name"] != name]


    def get_connections(self, properties):
        return []

    def on_search(self, binder, user_id, query, **kwargs):
        return [SearchNode.wrap_cancel()]


# ----------------------------------------------------------------------
# Input Blocks
# ----------------------------------------------------------------------


class InputBlock(BaseBlock):
    @abstractmethod
    def on_process(self, binder, user_id, statement):
        return self.reject()

    def process(self, binder, user_id, statement):
        # by pass input validation while skip node given
        required = self.property_value("required")
        if not required and statement.input is None:
            self.save(binder, None)
            return self.move()
        return self.on_process(binder, user_id, statement)

    def get_connections(self, properties):
        return [[BLOCK_MOVE, "Next"], [BLOCK_REJECT, "Reject"]]

    # this methods return saves value in state
    def save(self, binder, value):
        state = binder.on_load_state()
        key = self.property_value("key")
        state.data[key] = value
        binder.on_save_state(state.serialize())

    # this method return value from state
    def load(self, binder):
        state = binder.on_load_state()
        key = self.property_value("key")
        return state.data.get(key)

    def load_template(self):
        self.append_template_properties(
            [
                {
                    "text": "Key",
                    "name": "key",
                    "format": "string",
                    "input_type": "text",
                    "required": True,
                    "unique": True,
                    "auto": True,
                    "description": "Key used to store the data",
                    "value": None,
                },
                {
                    "text": "Prompt",
                    "name": "prompt",
                    "format": "string",
                    "input_type": "text",
                    "required": False,
                    "auto": True,
                    "description": "Display text before processing block",
                    "value": None,
                },
                {
                    "text": "Required",
                    "name": "required",
                    "format": "boolean",
                    "input_type": "checkbox",
                    "required": True,
                    "description": "If set to false this property become optional.",
                    "value": False,
                },
            ]
        )

    def on_search(self, binder, user_id, query, **kwargs):
        required = self.property_value("required")
        if required is not None and not required:
            resources = super(InputBlock, self).on_search(binder, user_id, query, **kwargs)
            resources.extend([SearchNode.wrap_skip()])
            return resources
        return super(InputBlock, self).on_search(binder, user_id, query, **kwargs)


class DecisionBlock(InputBlock):
    def before_process(self, binder, operator_id):
        pass

    def get_connections(self, *args, **kwargs):
        return [[BLOCK_REJECT, "Reject"]]

    def on_descriptor(self):
        return {
            "name": "Decision Block",
            "summary": "Maps a list of options to other blocks",
            "category": "input",
        }

    def on_process(self):
        pass

    def load_template(self):
        self.append_template_properties(
            [
                {
                    "text": "Prompt",
                    "name": "prompt",
                    "format": "string",
                    "input_type": "text",
                    "required": False,
                    "auto": True,
                    "description": "Display text before processing block",
                    "value": None,
                },
                {
                    "text": "Connections",
                    "name": "connections",
                    "format": "connections",
                    "input_type": "connections",
                    "required": True,
                    "unique": False,
                    "auto": True,
                    "description": "Maps a list of options to blocks",
                    "value": [],
                },
            ]
        )

        
class GoToBlock(InputBlock):
    def before_process(self, binder, operator_id):
        pass

    def get_connections(self, *args, **kwargs):
        return [[BLOCK_NEXT, "Next"]]

    def on_descriptor(self):
        return {
            "name": "GoTo Block",
            "summary": "Redirects to another block",
            "category": "input",
        }

    def on_process(self):
        pass

    def load_template(self):
        self.append_template_properties(
            [
                {
                    "text": "Prompt",
                    "name": "prompt",
                    "format": "string",
                    "input_type": "text",
                    "required": False,
                    "auto": True,
                    "description": "Display text before processing block",
                    "value": None,
                },
                {
                    "text": "Destination Block ID",
                    "name": "destination_block_id",
                    "format": "string",
                    "input_type": "text",
                    "required": True,
                    "auto": False,
                    "description": "The ID of the block to redirect to",
                    "value": None,
                },
            ]
        )
        

class InputDate(InputBlock):
    def on_descriptor(self):
        return {"name": "Date Input", "summary": "No description available", "category": "input"}

    def on_process(self, binder, user_id, statement):
        if statement.input:
            try:
                datetime.datetime.strptime(statement.input, "%Y-%m-%d")
                self.save(binder, statement.input)
                return self.move()
            except:
                pass
        return super(InputDate, self).on_process(binder, user_id, statement)


class InputDateTime(InputBlock):
    def on_descriptor(self):
        return {
            "name": "Date time Input",
            "summary": "No description available",
            "category": "input",
        }

    def on_process(self, binder, user_id, statement):
        if statement.input:
            try:
                datetime.datetime.strptime(statement.input, "%Y-%m-%d %H:%M:%S")
                self.save(binder, statement.input)
                return self.move()
            except:
                pass
        return super(InputDateTime, self).on_process(binder, user_id, statement)


class InputDuration(InputBlock):
    def on_descriptor(self):
        return {
            "name": "Duration Input",
            "summary": "No description available",
            "category": "input",
        }

    def on_process(self, binder, user_id, statement):
        if statement.input:
            try:
                dur = Duration(statement.input)
                if dur.to_seconds():
                    value = [int(dur.to_hours()), int(dur.to_minutes() % 60)]
                    self.save(binder, value)
                    return self.move()
            except:
                pass
        return super(InputDuration, self).on_process(binder, user_id, statement)


class InputEmail(InputBlock):
    def on_descriptor(self):
        return {
            "name": "Email Input",
            "summary": "Validates and saves input as email",
            "category": "input"
        }

    def on_process(self, binder, user_id, statement):
        email_regex = "^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$"
        if statement.input and re.search(email_regex, statement.input.lower()):
            self.save(binder, statement.input)
            return self.move()
        return super().on_process(binder, user_id, statement)



class InputFile(InputBlock):
    """Sends an InputFileNode to the user, the user must return (or statement.input )a JSON object
    with the following structure:

    {
        "file": "file contents...",
        "file_name": "file_name.txt",
        "file_size": 156244,
    }

    Where:
        + file: File contents encoded as a base64 string:
            "data:<mime_type>;base64,<base64 string ...>"
        + file_name: File name.
        + file_size: Size of the file in bytes.
    """

    def load_template(self):
        super().load_template()
        self.append_template_properties(
            [
                {
                    "text": "File type",
                    "name": "accept",
                    "format": "string",
                    "input_type": "text",
                    "required": True,
                    "unique": True,
                    "auto": True,
                    "description": "Valid file extensions",
                    "value": "",
                },
                {
                    "text": "Size",
                    "name": "size",
                    "format": "integer",
                    "input_type": "number",
                    "required": True,
                    "unique": True,
                    "auto": True,
                    "description": "Maximum file size in bytes",
                    "value": 1000000,
                },
            ]
        )

    def before_process(self, binder, operator_id):
        accept = self.property_value("accept")
        size = self.property_value("size")
        output = OutputStatement(operator_id)
        output.append_node(InputFileNode({"accept": accept, "size": size}))
        binder.post_message(output)

    def on_descriptor(self):
        return {"name": "File Input", "summary": "Shows a file input field", "category": "input"}

    def on_process(self, binder, user_id, statement):
        if statement.input:
            try:
                file = statement.input["file"]
                file_name = statement.input["file_name"]
                file_size = statement.input["file_size"]
                max_size = self.property_value("size") or 1000000
            except Exception as e:
                Log.error("InputFile.on_process", e)
                return self.reject()

            if max_size < file_size:
                output = OutputStatement(user_id)
                output.append_text(f"File should be smaller than {max_size} bytes")
                binder.post_message(output)
                return self.reject()

            base64_re = re.compile(r"^data:(?P<mimetype>[^;]+);base64,(?P<data>.+)$")
            match = base64_re.match(file)
            if match:
                self.save(binder, statement.input)
                return self.move()
        return self.reject()


class InputNumber(InputBlock):
    def on_descriptor(self):
        return {"name": "Number Input", "summary": "No description available", "category": "input"}

    def on_process(self, binder, user_id, statement):
        if statement.input:
            if isinstance(statement.input, int) or isinstance(statement.input, float):
                self.save(binder, statement.input)
                return self.move()
        return super(InputNumber, self).on_process(binder, user_id, statement)


class InputOAuth(InputBlock):
    def on_descriptor(self):
        return {"name": "OAuth Input", "summary": "No description available", "category": "input"}

    def on_process(self, binder, user_id, input):
        authorization_response = input.input
        component_name = self.property_value("component")
        component_object = binder.get_registry().get_component(binder, component_name)
        on_redirect = component_object.on_redirect(binder, authorization_response)
        if on_redirect:
            return self.accept()
        return self.reject()

    def load_template(self):
        self.append_template_properties(
            [
                {
                    "text": "Component",
                    "name": "component",
                    "format": "string",
                    "input_type": "component",
                    "search_filter": "OAuthProvider",
                    "required": True,
                    "description": "OAuth component used to handle the authorization",
                    "value": None,
                }
            ]
        )

    def get_connections(self, properties):
        return [[BLOCK_MOVE, "Next"], [BLOCK_REJECT, "Reject"]]


class InputPayment(InputBlock):
    def on_init(self):
        super(InputPayment, self).on_init()
        self.remove_template_properties("required")

    def on_descriptor(self):
        return {"name": "Payment Input", "summary": "No description available", "category": "input"}

    def on_process(self, binder, user_id, input):
        try:
            authorization_response = input.input
            params = Utils.parse_params(authorization_response)
            component_name = params["component"]
            component_object = binder.get_registry().get_component(binder, component_name)
            on_redirect = component_object.on_redirect(binder, authorization_response)
            if on_redirect:
                return self.move()
        except:
            pass
        return self.reject()

    def load_template(self):
        self.append_template_properties(
            [
                {
                    "text": "Component",
                    "name": "component",
                    "format": "string",
                    "input_type": "component",
                    "search_filter": "PaymentProvider",
                    "required": True,
                    "description": "Payment component used to handle the authorization",
                    "value": None,
                }
            ]
        )

    def get_connections(self, properties):
        return [[BLOCK_MOVE, "Next"], [BLOCK_REJECT, "Reject"]]


class InputSearchable(InputBlock):
    def on_descriptor(self):
        return {
            "name": "Searchable Input",
            "summary": "No description available",
            "category": "input",
        }

    def on_process(self, binder, user_id, input):
        component_name = self.property_value("component")
        component_object = binder.get_registry().get_component(binder, component_name)
        state = binder.on_load_state()
        package = state.skill["package"]

        real_user_id = binder.on_load_state().user_id

        if isinstance(input.input, str):
            query = input.input
            item = component_object.on_query_search(
                binder, real_user_id, package, self, query, skill=state.skill
            )
            if item:
                valid = component_object.on_verify_input(
                    binder, real_user_id, package, self, item, skill=state.skill
                )
                if valid:
                    self.save(binder, item)
                    return self.move()
        else:
            item = input.input
            if item:
                valid = component_object.on_verify_input(
                    binder, real_user_id, package, self, item, skill=state.skill
                )
                if valid:
                    self.save(binder, item)
                    return self.move()

        return super().on_process(binder, user_id, input)

    def load_template(self):
        super(InputSearchable, self).load_template()
        self.append_template_properties(
            [
                {
                    "text": "Component",
                    "name": "component",
                    "format": "string",
                    "input_type": "search",
                    "search_filter": "SkillProvider",
                    "required": True,
                    "description": "Skill provider userd to handle the search",
                    "value": None,
                },
                {
                    "text": "Model",
                    "name": "model",
                    "format": "string",
                    "input_type": "text",
                    "required": True,
                    "description": "<Description of property.>",
                    "value": None,
                },
            ]
        )

    def on_search(self, binder, user_id, query, **kwargs):
        real_user_id = binder.on_load_state().user_id
        component_name = self.property_value("component")
        component_object = binder.get_registry().get_component(binder, component_name)
        state = binder.on_load_state()
        package = state.skill["package"]
        result = component_object.on_search(
            binder, real_user_id, package, self, query, skill=state.skill
        )
        resources = super(InputSearchable, self).on_search(binder, user_id, query, **kwargs)
        resources.extend(result)
        return resources


class InputSelection(InputBlock):
    def on_descriptor(self):
        return {
            "name": "Selection Input",
            "summary": "No description available",
            "category": "input",
        }

    def on_process(self, binder, user_id, statement):
        if statement.input:
            if self._in_selection(statement):
                value = statement.input
                self.save(binder, value)
                return self.move()
            fuzzy_item = self._fuzzy_item(statement)
            if fuzzy_item:
                value = fuzzy_item
                self.save(binder, value)
                return self.move()
        return super(InputSelection, self).on_process(binder, user_id, statement)

    def load_template(self):
        super(InputSelection, self).load_template()
        self.append_template_properties(
            [
                {
                    "text": "Selections",
                    "name": "selections",
                    "format": "json",
                    "input_type": "textarea",
                    "required": True,
                    "description": "List of options",
                    "value": [["draft", "Draft"]],
                }
            ]
        )

    # def get_connections(self, properties):
    #     connections = super(InputBlock, self).get_connections(properties)
    #     for idx, val in enumerate(self.property_value('selections')):
    #         pass
    #     return connections

    def _in_selection(self, statement):
        for item in self.property_value("selections"):
            if item[0] == statement.input:
                return True
        return False

    def _fuzzy_item(self, statement):
        for item in self.property_value("selections"):
            if item[1].lower() == statement.input.lower():
                return item[0]
        return None

    def on_search(self, binder, user_id, query, **kwargs):
        result = []
        for index, item in enumerate(self.property_value("selections")):
            txt, val = item[1], item[0]
            if query.lower() in txt.lower():
                result.append(SearchNode.wrap_text(txt, val))
        resources = super(InputSelection, self).on_search(binder, user_id, query, **kwargs)
        resources.extend(result)
        return resources


class InputSkill(InputBlock):
    """ """

    def on_descriptor(self):
        return {"name": "Skill Input", "summary": "Passes user input to skill", "category": "input"}

    def on_process(self, binder, user_id, statement):
        component_name = self.property_value("component")
        component_object = binder.get_registry().get_component(binder, component_name)
        state = binder.on_load_state()
        package = state.skill["package"]

        result = component_object.on_execute(
            binder,
            user_id,
            package,
            state.data,
            statement,
            properties=self.properties,
            skill=state.skill,
        )
        if result:
            self.context["result"] = result
            self.context["input"] = state.data
            nodes = self.property_value("nodes")
            if nodes:
                output = OutputStatement(user_id)
                for item in nodes:
                    if item["node"] == "big.bot.core.iframe":
                        template = Template(item["content"])
                        html = template.render(self.context)
                        output.append_node(IFrameNode(html))
                        binder.post_message(output)
                    elif item["node"] == "big.bot.core.text":
                        template = Template(item["content"])
                        html = template.render(self.context)
                        output.append_text(html)
                        binder.post_message(output)
            return self.move()
        return super().on_process(binder, user_id, statement)

    def on_search(self, binder, user_id, query):
        component_name = self.property_value("component")
        component_object = binder.get_registry().get_component(binder, component_name)
        state = binder.on_load_state()
        package = state.skill["package"]

        try:
            result = component_object.on_search(
                binder,
                user_id,
                package,
                state.data,
                query,
                properties=self.properties,
                skill=state.skill,
            )
        except Exception as e:
            Log.error("Exception", e)
            result = [SearchNode.wrap_cancel()]

        return result

    def load_template(self):
        super(InputSkill, self).load_template()
        self.append_template_properties(
            [
                {
                    "text": "Output Nodes",
                    "name": "nodes",
                    "format": "json",
                    "input_type": "nodes",
                    "required": True,
                    "description": "Skill provider",
                    "value": [],
                }
            ]
        )


class InputText(InputBlock):
    def on_descriptor(self):
        return {"name": "Text Input", "summary": "No description available", "category": "input"}

    def on_process(self, binder, user_id, statement):
        if statement.input:
            self.save(binder, statement.input)
            return self.move()
        return super(InputText, self).on_process(binder, user_id, statement)


# ----------------------------------------------------------------------
# Interpreter Blocks
# ----------------------------------------------------------------------


class InterpreterBlock(BaseBlock):
    def __init__(self, context, id, properties, connections):
        super(InterpreterBlock, self).__init__(context, id, properties, connections)
        self.context = context
        self.id = id
        self.properties = properties
        self.connections = connections

    @abstractmethod
    def on_process(self, binder, user_id):
        return self.move_x()

    def process(self, binder, user_id):
        return self.on_process(binder, user_id)

    def get_connections(self, properties):
        return [[BLOCK_MOVE, "Next"], [BLOCK_MOVE_X, "Reject"]]

    def load_template(self):
        self.append_template_properties(
            [
                {
                    "text": "Component",
                    "name": "component",
                    "format": "string",
                    "input_type": "component",
                    "required": True,
                    "description": "Skill provider",
                    "search_filter": "SkillProvider",
                    "value": None,
                }
            ]
        )


class DataExchange(InterpreterBlock):
    def on_descriptor(self):
        return {
            "category": "exchange",
            "name": "Data Exchange",
            "summary": "Calls a data exchange component",
        }

    def on_process(self, binder, operator_id):
        component_name = self.property_value("component")
        component_object = binder.get_registry().get_data_exchange(binder, component_name)
        state = binder.on_load_state()
        data = state.data
        package = state.skill["package"]

        input = self.property_value("input")
        if input:
            tmp = {}
            for from_, to in input:
                tmp[to] = data.get(from_)
            input = tmp
        else:
            input = {}

        result = component_object(binder, operator_id, package, data, **input)

        output = self.property_value("output")
        if output and result:
            for from_, to in output:
                data[to] = result.get(from_)
        elif result:
            for key in result:
                data[key] = result[key]

        state.data = data
        binder.on_save_state(state.serialize())

        return self.move()

    def load_template(self):
        super().load_template()
        self.append_template_properties(
            [
                {
                    "text": "Input Data",
                    "name": "input",
                    "format": "json",
                    "input_type": "nodes",
                    "required": False,
                    "description": "Input data for the exchange function",
                    "value": [],
                },
                {
                    "text": "Output Data",
                    "name": "output",
                    "format": "json",
                    "input_type": "nodes",
                    "required": False,
                    "description": "Output data for the exchange function",
                    "value": [],
                },
            ]
        )


class InterpreterSkill(InterpreterBlock):
    def on_descriptor(self):
        return {
            "name": "Skill Interpreter",
            "summary": "This block runs logic.",
            "category": "interpreter",
        }

    def on_process(self, binder, user_id):
        component_name = self.property_value("component")
        component_object = binder.get_registry().get_component(binder, component_name)
        state = binder.on_load_state()
        package = state.skill["package"]

        result = component_object.on_execute(
            binder, user_id, package, state.data, properties=self.properties, skill=state.skill
        )
        if result:
            self.context["result"] = result
            self.context["input"] = state.data
            # self.save(binder, result)
            nodes = self.property_value("nodes")
            if nodes:
                output = OutputStatement(user_id)
                for item in nodes:
                    if item["node"] == "big.bot.core.text":
                        template = Template(item["content"])
                        html = template.render(self.context)
                        output.append_text(html)
                        binder.post_message(output)
                    elif item["node"] == "big.bot.core.iframe":
                        template = Template(item["content"])
                        html = template.render(self.context)
                        output.append_node(IFrameNode(html))
                        binder.post_message(output)
                    pass
            return self.move()
        return super().on_process(binder, user_id)

    def load_template(self):
        super(InterpreterSkill, self).load_template()
        self.append_template_properties(
            [
                {
                    "text": "Output Nodes",
                    "name": "nodes",
                    "format": "json",
                    "input_type": "nodes",
                    "required": True,
                    "description": "Nodes used to render the result",
                    "value": [],
                }
            ]
        )


# ----------------------------------------------------------------------
# Prompt Blocks
# ----------------------------------------------------------------------


class PromptBlock(BaseBlock):
    def get_connections(self, properties):
        return [[BLOCK_MOVE, "Next"]]

    def load_template(self):
        self.append_template_properties(
            [
                {
                    "text": "Read",
                    "name": "read",
                    "format": "string",
                    "required": False,
                    "unique": True,
                    "auto": True,
                    "description": "Reads data from the data instead of using the set value",
                    "value": None,
                }
            ]
        )

    @abstractmethod
    def on_process(self, binder, user_id):
        return self.move()

    def process(self, binder, user_id):
        return self.on_process(binder, user_id)


class PromptBinary(PromptBlock):
    def on_descriptor(self):
        return {"name": "Binary", "summary": "No description available", "category": "prompt"}

    def on_process(self, binder, user_id):
        binary = self.property_value("binary")
        output = OutputStatement(user_id)
        output.append_node(BinaryNode(binary))
        binder.post_message(output)
        return super(PromptBinary, self).on_process(binder, user_id)

    def load_template(self):
        super().load_template()
        self.append_template_properties(
            [
                {
                    "text": "Binary",
                    "name": "binary",
                    "format": "binary",
                    "input_type": "file",
                    "file_limit": 1000000,
                    "mime_types": ["*/*"],
                    "required": True,
                    "description": "Binary File",
                    "value": None,
                },
            ]
        )


class PromptChatPlatform(PromptBlock):
    def on_descriptor(self):
        return {
            "name": "Chat Platforms",
            "summary": "No description available",
            "category": "prompt",
        }

    def on_process(self, binder, user_id):
        # load value from template for further integrations
        real_user_id = binder.on_load_state().user_id
        # base64 encode user id as payload
        b64_bytes = base64.b64encode(str(real_user_id).encode("utf-8"))
        payload = b64_bytes.decode("utf-8")
        data = {
            "platforms": [
                {
                    "name": "Telegram",
                    "icon": "data:image/png;base64,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",
                    "url": "https://t.me/randomNameTestBot?start=" + payload,
                }
            ]
        }
        meta = {"header": "Available Platforms", "button_text": "Chat now"}
        chat_platform = ChatPlatformNode(data, meta)

        output = OutputStatement(user_id)
        output.append_node(chat_platform)
        binder.post_message(output)
        return super(PromptChatPlatform, self).on_process(binder, user_id)


class PromptDate(PromptBlock):
    def on_descriptor(self):
        return {"name": "Date", "summary": "No description available", "category": "prompt"}

    def on_process(self, binder, user_id):
        output = OutputStatement(user_id)
        output.append_node(DateNode(None))
        binder.post_message(output)
        return super(PromptDate, self).on_process(binder, user_id)

    def load_template(self):
        super().load_template()
        self.append_template_properties(
            [
                {
                    "text": "Date",
                    "name": "date",
                    "format": "time",
                    "input_type": "date",
                    "unique": False,
                    "auto": False,
                    "description": "Date",
                }
            ]
        )


class PromptDateTime(PromptBlock):
    def on_descriptor(self):
        return {"name": "Date Time", "summary": "No description available", "category": "prompt"}

    def on_process(self, binder, user_id):
        output = OutputStatement(user_id)
        output.append_node(DateTimeNode(None))
        binder.post_message(output)
        return super(PromptDateTime, self).on_process(binder, user_id)

    def load_template(self):
        super().load_template()
        self.append_template_properties(
            [
                {
                    "text": "Datetime",
                    "name": "datetime",
                    "format": "time",
                    "input_type": "datetime",
                    "unique": False,
                    "auto": False,
                    "description": "Hour and Date",
                }
            ]
        )


class PromptDuration(PromptBlock):
    def on_descriptor(self):
        return {"name": "Duration", "summary": "No description available", "category": "prompt"}

    def on_process(self, binder, user_id):
        output = OutputStatement(user_id)
        output.append_node(DurationNode(None))
        binder.post_message(output)
        return super(PromptDuration, self).on_process(binder, user_id)

    def load_template(self):
        super().load_template()
        self.append_template_properties(
            [
                {
                    "text": "Duration",
                    "name": "time",
                    "format": "time",
                    "input_type": "time",
                    "unique": False,
                    "auto": False,
                    "description": "Hour",
                }
            ]
        )


class PromptImage(PromptBlock):
    def on_descriptor(self):
        return {"name": "Image", "summary": "No description available", "category": "prompt"}

    def on_process(self, binder, user_id):
        image = self.property_value("image")
        output = OutputStatement(user_id)
        output.append_node(ImageNode(image))
        binder.post_message(output)
        return super(PromptImage, self).on_process(binder, user_id)

    def load_template(self):
        super().load_template()
        self.append_template_properties(
            [
                {
                    "text": "Image",
                    "name": "image",
                    "format": "binary",
                    "input_type": "file",
                    "file_limit": 1000000,
                    "mime_types": ["image/jpeg", "image/png", "image/gif"],
                    "required": True,
                    "description": "Image File",
                    "value": None,
                },
            ]
        )


class PromptPayment(PromptBlock):
    def on_descriptor(self):
        return {"name": "Payment", "summary": "No description available", "category": "prompt"}

    def on_process(self, binder, user_id):
        real_user_id = binder.on_load_state().user_id
        amount = self.property_value("amount")
        currency_code = "USD"
        # this is hardcoded add props for same
        meta = {
            "charge_summary": "You have to pay",
            "currency_code": currency_code,
            "currency_symbol": "$",
            "button_text": "Pay " + str(amount) + " " + currency_code,
            "payment_services": [],
        }
        objects = binder.get_registry().payment_providers(binder)
        for component_object in objects:
            payment_url = component_object.get_payment_url(
                binder, real_user_id, amount, currency_code
            )
            payment_method = component_object.get_meta()
            # need improvement for including such meta
            if "name" not in payment_method:
                payment_method["name"] = "None"
            elif "icon" not in payment_method:
                payment_method["icon"] = "https://commons.wikimedia.org/wiki/File:PayPal.svg"
            payment_method["payment_url"] = payment_url
            meta["payment_services"].append(payment_method)
            pass
        payment_node = PaymentNode(amount, meta)
        output = OutputStatement(user_id)
        output.append_node(payment_node)
        binder.post_message(output)
        Log.info("PaymentNode", payment_node.serialize())
        return super().on_process(binder, user_id)

    def load_template(self):
        super().load_template()
        self.append_template_properties(
            [
                {
                    "text": "Amount",
                    "name": "amount",
                    "format": "float",
                    "input_type": "number",
                    "required": True,
                    "description": "Amount to pay",
                    "value": 0.00,
                },
            ]
        )


class PromptPreview(PromptBlock):
    def on_descriptor(self):
        return {"category": "prompt", "name": "Preview", "summary": "Previews a URL"}

    def load_template(self):
        super().load_template()
        self.append_template_properties(
            [
                {
                    "text": "URL",
                    "name": "url",
                    "format": "string",
                    "input_type": "url",
                    "required": True,
                    "description": "URL to display",
                    "value": "https://example.com",
                }
            ]
        )

    def on_process(self, binder, user_id):
        url = self.property_value("url")
        output = OutputStatement(user_id)
        binder.append_node(PreviewNode(url))
        binder.post_message(output)
        return super().on_process(binder, user_id)


class PromptText(PromptBlock):
    def on_descriptor(self):
        return {"name": "Text", "summary": "No description available", "category": "prompt"}

    def on_process(self, binder, user_id):
        output = OutputStatement(user_id)
        output.append_text(text=self._get_display_text())
        binder.post_message(output)
        return super(PromptText, self).on_process(binder, user_id)

    def load_template(self):
        super().load_template()
        self.append_template_properties(
            [
                {
                    "text": "Text Primary",
                    "name": "primary_text",
                    "format": "array",
                    "input_type": "text",
                    "required": True,
                    "description": "List of strings to display",
                    "value": [],
                },
            ]
        )

    def _get_display_text(self):
        value = self.property_value("primary_text")
        pattern = random.choice(value)
        template = Template(pattern)
        html = template.render(self.context)
        return html


# ----------------------------------------------------------------------
# Terminal Blocks
# ----------------------------------------------------------------------


class TerminalBlock(BaseBlock):
    def on_descriptor(self):
        return {
            "name": "Terminate",
            "summary": "This block terminate the workflow.",
            "category": "terminal",
        }

    def process(self, binder, user_id):
        return self.move()

    def get_connections(self, properties):
        return []

    def load_template(self):
        self.append_template_properties(
            [
                {
                    "text": "Post Action",
                    "name": "action",
                    "format": "enum",
                    "input_type": "select",
                    "required": True,
                    "description": "Actio to execute after",
                    "enum": [
                        {"name": "Do Nothing", "value": 0},
                        {"name": "Start Skill", "value": 1},
                        {"name": "Hand over user", "value": 2},
                        {"name": "Hand over group", "value": 3},
                    ],
                    "value": 0,
                },
                {
                    "text": "Post Skill",
                    "name": "post_skill",
                    "format": "string",
                    "input_type": "text",
                    "required": False,
                    "description": "Skill to call after execution",
                    "value": None,
                },
                {
                    "text": "Template",
                    "name": "template",
                    "format": "string",
                    "input_type": "text",
                    "required": False,
                    "description": "Template used when handing over a skill",
                    "value": "",
                },
            ]
        )

    def post_skill(self):
        return self.property_value("post_skill")
