from abc import ABC, abstractmethod
import datetime
import random
import re
import spacy
from typing import List, Tuple, Union
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


class BlockNotFoundException(Exception):
    pass


class ComponentNotFoundException(Exception):
    pass


def get_block_by_id(binder, skill, block_id):
    block_data = next((item for item in skill["blocks"] if item["id"] == block_id), None)
    if block_data is None:
        raise BlockNotFoundException(f"Block not found for id: {block_id}")
    component = block_data["component"]
    blocks = [b for b in binder.get_registry().blocks if f"{b.__module__}.{b.__name__}" == component]
    if not blocks:
        raise ComponentNotFoundException(f"Component not found for id: {block_id}")
    block = blocks[0]
    connections = block_data.get("connections")
    return block(binder.on_context(), block_data["id"], block_data["properties"], connections)


def get_block_by_property(binder, skill, key_name, key_value):
    matches = [item for item in skill["blocks"]
               if item["component"] in (f"{b.__module__}.{b.__name__}" for b in binder.get_registry().blocks)
               and block_obj := block(binder.on_context(), item["id"], item["properties"], item.get("connections"))
               and block_obj.property_value(key_name) == key_value]
    if not matches:
        raise BlockNotFoundException(f"Block not found for property {key_name} with value {key_value}")
    return matches[0]


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
        self.component = f"{self.__class__.__module__}.{self.__class__.__name__}"
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
        return next((prop["value"] for prop in self.properties if prop["name"] == key), None)

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
        # bypass input validation while skip node given
        required = self.property_value("required")
        if not required and statement.input is None:
            self.save(binder, None)
            return self.move()
        return self.on_process(binder, user_id, statement)

    def get_connections(self, properties):
        return [[BLOCK_MOVE, "Next"], [BLOCK_REJECT, "Reject"]]

    # this method saves a value in the state
    def save(self, binder, value):
        state = binder.load_state()
        key = self.property_value("key")
        state.data[key] = value
        binder.save_state(state)

    # this method returns a value from the state
    def load(self, binder):
        state = binder.load_state()
        key = self.property_value("key")
        return state.data.get(key)

    def load_template(self):
        self.add_template_property(
            "key",
            "string",
            "text",
            required=True,
            unique=True,
            auto=True,
            description="Key used to store the data",
        )
        self.add_template_property(
            "prompt",
            "string",
            "text",
            required=False,
            auto=True,
            description="Display text before processing block",
        )
        self.add_template_property(
            "required",
            "boolean",
            "checkbox",
            required=True,
            description="If set to false this property becomes optional.",
            value=False,
        )

    def on_search(self, binder, user_id, query, **kwargs):
        required = self.property_value("required")
        if required is not None and not required:
            resources = super().on_search(binder, user_id, query, **kwargs)
            resources.append(SearchNode.wrap_skip())
            return resources
        return super().on_search(binder, user_id, query, **kwargs)

class DecisionBlock(InputBlock):
    def on_descriptor(self):
        return {
            "name": "Decision Block",
            "summary": "Maps a list of options to other blocks",
            "category": "input",
        }

    def load_template(self):
        super().load_template()
        self.append_template_properties([
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
        ])

    def on_process(self, binder, user_id, statement):
        options = self.property_value("connections")

        for option in options:
            value = option["value"]
            condition = option["condition"]

            if condition is None or self.evaluate_condition(condition, statement):
                block_id = value["block_id"]
                block = binder.get_block_by_id(block_id)

                if block is not None:
                    binder.set_current_block_id(block_id)
                    return self.move()

        return self.reject()

    def evaluate_condition(self, condition, statement):
        if not condition:
            return True

        if "input" in condition:
            input_value = statement.input
            expected_value = condition["input"]
            return input_value == expected_value

        if "intent" in condition:
            intent_value = statement.intent
            expected_value = condition["intent"]
            return intent_value == expected_value

        return False


class GoToBlock(InputBlock):
    def before_process(self, binder, operator_id):
        pass

    def get_connections(self, properties):
        return [[BLOCK_NEXT, "Next"]]

    def on_descriptor(self):
        return {
            "name": "GoTo Block",
            "summary": "Redirects to another block",
            "category": "input",
        }

    def on_process(self, binder, user_id, statement):
        destination_block_id = self.property_value("destination_block_id")
        binder.on_save_data("next_block_id", destination_block_id)
        return self.move()

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
            except ValueError:
                pass
        return super().on_process(binder, user_id, statement)


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
            except ValueError:
                pass
        return super().on_process(binder, user_id, statement)


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
            except (ValueError, TypeError):
                pass
        return super().on_process(binder, user_id, statement)


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
    def __init__(self):
        super().__init__()
        self.accept = InputProperty("accept", "string", required=True, description="Valid file extensions")
        self.size = InputProperty("size", "integer", required=True, default=1000000, description="Maximum file size in bytes")

    def on_descriptor(self):
        return {"name": "File Input", "summary": "Shows a file input field", "category": "input"}

    def on_process(self, binder, user_id, statement):
        if statement.input:
            try:
                file = statement.input["file"]
                file_name = statement.input["file_name"]
                file_size = statement.input["file_size"]
                max_size = self.size.value or 1000000
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

    def on_template_load(self):
        self.accept.load_from_template(self.template)
        self.size.load_from_template(self.template)
        super().on_template_load()

    def before_process(self, binder, operator_id):
        output = OutputStatement(operator_id)
        output.append_node(InputFileNode({"accept": self.accept.value, "size": self.size.value}))
        binder.post_message(output)


class InputNumber(InputBlock):
    def on_descriptor(self):
        return {"name": "Number Input", "summary": "No description available", "category": "input"}

    def on_process(self, binder, user_id, statement):
        if statement.input:
            if isinstance(statement.input, int) or isinstance(statement.input, float):
                self.save(binder, statement.input)
                return self.move()
        return super().on_process(binder, user_id, statement)

class InputOAuth(InputBlock):
    def on_descriptor(self):
        return {
            "name": "OAuth Input",
            "summary": "No description available",
            "category": "input",
        }

    def on_process(self, binder, user_id, statement):
        authorization_response = statement.input
        component_name = self.property_value("component")
        component_object = binder.get_registry().get_component(binder, component_name)
        on_redirect = component_object.on_redirect(binder, authorization_response)
        if on_redirect:
            return self.accept()
        return self.reject()

    def load_template(self):
        super().load_template()
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
        return [
            [BLOCK_MOVE, "Next"],
            [BLOCK_REJECT, "Reject"]
        ]


class InputPayment(InputBlock):
    def on_init(self):
        super().on_init()
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
        except Exception:
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

        real_user_id = state.user_id

        item = input.input
        if isinstance(item, str):
            query = item
            item = component_object.on_query_search(
                binder, real_user_id, package, self, query, skill=state.skill
            )
        if not item:
            return super().on_process(binder, user_id, input)

        valid = component_object.on_verify_input(
            binder, real_user_id, package, self, item, skill=state.skill
        )
        if not valid:
            return super().on_process(binder, user_id, input)

        self.save(binder, item)
        return self.move()

    def load_template(self):
        super().load_template()
        self.append_template_properties([
            {
                "text": "Component",
                "name": "component",
                "format": "string",
                "input_type": "search",
                "search_filter": "SkillProvider",
                "required": True,
                "description": "Skill provider used to handle the search",
                "value": None,
            },
            {
                "text": "Model",
                "name": "model",
                "format": "string",
                "input_type": "text",
                "required": True,
                "description": "<Description of property>",
                "value": None,
            },
        ])

    def on_search(self, binder, user_id, query, **kwargs):
        component_name = self.property_value("component")
        component_object = binder.get_registry().get_component(binder, component_name)
        state = binder.on_load_state()
        package = state.skill["package"]

        result = component_object.on_search(
            binder, state.user_id, package, self, query, skill=state.skill
        )

        resources = super().on_search(binder, user_id, query, **kwargs)
        resources.extend(result)
        return resources


import spacy

class InputSelection(InputBlock):
    def __init__(self, nlp=None):
        super().__init__()
        if nlp is None:
            nlp = spacy.load("en_core_web_sm")
        self.nlp = nlp

    def on_descriptor(self):
        return {
            "name": "Selection Input",
            "summary": "No description available",
            "category": "input",
        }

    def on_process(self, binder, user_id, statement):
        if statement.input:
            value = self._get_value(statement)
            if value is not None:
                self.save(binder, value)
                return self.move()
        return super().on_process(binder, user_id, statement)

    def load_template(self):
        super().load_template()
        self.append_template_properties([
            {
                "text": "Selections",
                "name": "selections",
                "format": "json",
                "input_type": "textarea",
                "required": True,
                "description": "List of options",
                "value": [["draft", "Draft"]],
            }
        ])

    def _get_value(self, statement):
        value = statement.input
        if self._in_selection(value):
            return value
        fuzzy_item = self._fuzzy_item(value)
        if fuzzy_item is not None:
            return fuzzy_item
        augmented_results = self._augment_results(value)
        if augmented_results:
            return augmented_results[0]
        return None

    def _in_selection(self, value):
        return any(item[0] == value for item in self.property_value("selections"))

    def _fuzzy_item(self, value):
        for item in self.property_value("selections"):
            if item[1].lower() == value.lower():
                return item[0]
        return None

    def _augment_results(self, value):
        doc = self.nlp(value)
        tokens = [token for token in doc if not token.is_stop]
        results = []
        for index, item in enumerate(self.property_value("selections")):
            txt, val = item[1], item[0]
            item_doc = self.nlp(txt)
            item_tokens = [token for token in item_doc if not token.is_stop]
            score = doc.similarity(item_doc)
            for token in tokens:
                token_score = max(token.similarity(item_token) for item_token in item_tokens)
                score += token_score
            score /= len(tokens) + len(item_tokens)
            results.append((score, val))
        results.sort(reverse=True)
        return [result[1] for result in results]

    def on_search(self, binder, user_id, query, **kwargs):
        result = []
        for index, item in enumerate(self.property_value("selections")):
            txt, val = item[1], item[0]
            if query.lower() in txt.lower():
                result.append(SearchNode.wrap_text(txt, val))
        fuzzy_results = self._fuzzy_search(query)
        resources = super().on_search(binder, user_id, query, **kwargs)
        resources.extend(result + fuzzy_results)
        return resources

    def _similarity(self, text1, text2):
        doc1 = self.nlp(text1)
        doc2 = self.nlp(text2)
        return doc1.similarity(doc2)

    def _fuzzy_search(self, query):
        results = []
        for index, item in enumerate(self.property_value("selections")):
            txt, val = item[1], item[0]
            if query.lower() in txt.lower():
                results.append((0, val))
        results.extend([(self._similarity(query, item[1]), item[0]) for item in self.property_value("selections")])
        results.sort(reverse=True)
        return [SearchNode.wrap_text(item[1], item[0]) for item in results]


class InputSkill(InputBlock):
    """An input block that passes user input to a skill"""

    def on_descriptor(self):
        """Returns a dictionary containing metadata about this input block"""
        return {
            "name": "Skill Input",
            "summary": "Passes user input to skill",
            "category": "input"
        }

    def on_process(self, binder, user_id, statement):
        """Processes the user's input statement"""
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
                    template = Template(item["content"])
                    html = template.render(self.context)

                    if item["node"] == "big.bot.core.iframe":
                        output.append_node(IFrameNode(html))
                    elif item["node"] == "big.bot.core.text":
                        output.append_text(html)

                binder.post_message(output)

            return self.move()

        return super().on_process(binder, user_id, statement)

    def on_search(self, binder, user_id, query):
        """Searches for the user's query"""
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
        """Loads the template for this input block"""
        super().load_template()
        self.append_template_properties([
            {
                "text": "Output Nodes",
                "name": "nodes",
                "format": "json",
                "input_type": "nodes",
                "required": True,
                "description": "Nodes to output to the user",
                "value": [],
            }
        ])


class InputText(InputBlock):
    def on_descriptor(self):
        return {
            "name": "Text Input",
            "summary": "No description available",
            "category": "input"
        }

    def on_process(self, binder, user_id, statement):
        if statement.input:
            self.save(binder, statement.input)
            return self.move()

        return super().on_process(binder, user_id, statement)



# ----------------------------------------------------------------------
# Interpreter Blocks
# ----------------------------------------------------------------------

class InterpreterBlock(BaseBlock):
    def __init__(self, context, id, properties, connections):
        super().__init__(context, id, properties, connections)

    def on_process(self, binder, user_id):
        return self.move_x()

    def process(self, binder, user_id):
        return self.on_process(binder, user_id)

    def get_connections(self, properties):
        return [[BLOCK_MOVE, "Next"], [BLOCK_MOVE_X, "Reject"]]

    def load_template(self):
        self.append_template_properties([
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
        ])


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
        self.append_template_properties([
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
            }
        ])


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

            nodes = self.property_value("nodes")
            if nodes:
                output = OutputStatement(user_id)
                for item in


# ----------------------------------------------------------------------
# Prompt Blocks
# ----------------------------------------------------------------------


class PromptBlock(BaseBlock):
    def get_connections(self, properties):
        return [[BLOCK_MOVE, "Next"]]

    def load_template(self):
        super().load_template()
        self.append_template_properties([
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
        ])

    @abstractmethod
    def on_process(self, binder, user_id):
        return self.move()

    def process(self, binder, user_id):
        return self.on_process(binder, user_id)


class PromptBinary(PromptBlock):
    def on_descriptor(self):
        return {
            "name": "Binary",
            "summary": "No description available",
            "category": "prompt"
        }

    def load_template(self):
        super().load_template()
        self.append_template_properties([
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
        ])

    def on_process(self, binder, user_id):
        binary = self.property_value("binary")
        output = OutputStatement(user_id)
        output.append_node(BinaryNode(binary))
        binder.post_message(output)
        return super().on_process(binder, user_id)


class PromptChatPlatform(PromptBlock):
    def on_descriptor(self):
        return {
            "name": "Chat Platforms",
            "summary": "No description available",
            "category": "prompt"
        }

    def on_process(self, binder, user_id):
        real_user_id = binder.on_load_state().user_id
        b64_bytes = base64.b64encode(str(real_user_id).encode("utf-8"))
        payload = b64_bytes.decode("utf-8")
        data = {
            "platforms": [
                {
                    "name": "Telegram",
                    "url": f"https://t.me/randomNameTestBot?start={payload}",
                }
            ]
        }
        meta = {"header": "Available Platforms", "button_text": "Chat now"}
        chat_platform = ChatPlatformNode(data, meta)

        output = OutputStatement(user_id)
        output.append_node(chat_platform)
        binder.post_message(output)
        return super().on_process(binder, user_id)


class PromptTimeBlock(PromptBlock):
    def get_output_node(self):
        return None

    @abstractmethod
    def get_time_node(self, value):
        pass

    def on_process(self, binder, user_id):
        output = OutputStatement(user_id)
        value = self.property_value("time")
        output_node = self.get_time_node(value)
        if output_node:
            output.append_node(output_node)
        binder.post_message(output)
        return super(PromptTimeBlock, self).on_process(binder, user_id)

    def load_template(self):
        super().load_template()
        self.append_template_properties(
            [
                {
                    "text": self.__class__.__name__,
                    "name": "time",
                    "format": "time",
                    "unique": False,
                    "auto": False,
                    "description": self.__class__.__name__,
                }
            ]
        )

class PromptDate(PromptTimeBlock):
    def get_output_node(self):
        return DateNode(None)

    def get_time_node(self, value):
        return self.get_output_node()

class PromptDateTime(PromptTimeBlock):
    def get_output_node(self):
        return DateTimeNode(None)

    def get_time_node(self, value):
        return self.get_output_node()

class PromptDuration(PromptTimeBlock):
    def get_output_node(self):
        return DurationNode(None)

    def get_time_node(self, value):
        return self.get_output_node()


class PromptImage(PromptBlock):
    def __init__(self):
        super().__init__()
        self.descriptor = {"name": "Image", "summary": "No description available", "category": "prompt"}

    def on_process(self, binder, user_id):
        image = self.property_value("image")
        output = OutputStatement(user_id)
        output.append_node(ImageNode(image))
        binder.post_message(output)
        return super().on_process(binder, user_id)

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

        payment_services = self._get_payment_services(binder, real_user_id, amount, currency_code)
        payment_node = PaymentNode(amount, self._get_payment_meta(amount, currency_code, payment_services))

        output = OutputStatement(user_id)
        output.append_node(payment_node)
        binder.post_message(output)
        Log.info("PaymentNode", payment_node.serialize())

        return super().on_process(binder, user_id)

    def load_template(self):
        super().load_template()
        self.append_template_properties([
            {
                "text": "Amount",
                "name": "amount",
                "format": "float",
                "input_type": "number",
                "required": True,
                "description": "Amount to pay",
                "value": 0.00,
            },
        ])

    def _get_payment_services(self, binder, user_id, amount, currency_code):
        payment_services = []

        objects = binder.get_registry().payment_providers(binder)
        for component_object in objects:
            payment_url = component_object.get_payment_url(
                binder, user_id, amount, currency_code
            )
            payment_method = component_object.get_meta()

            if "name" not in payment_method:
                payment_method["name"] = "None"
            if "icon" not in payment_method:
                payment_method["icon"] = "https://commons.wikimedia.org/wiki/File:PayPal.svg"

            payment_method["payment_url"] = payment_url
            payment_services.append(payment_method)

        return payment_services

    def _get_payment_meta(self, amount, currency_code, payment_services):
        return {
            "charge_summary": "You have to pay",
            "currency_code": currency_code,
            "currency_symbol": "$",
            "button_text": f"Pay {amount} {currency_code}",
            "payment_services": payment_services,
        }


class PromptPreview(PromptBlock):
    def on_descriptor(self):
        return {
            "category": "prompt",
            "name": "Preview",
            "summary": "Previews a URL"
        }

    def load_template(self):
        super().load_template()
        self.append_template_properties([
            {
                "text": "URL",
                "name": "url",
                "format": "string",
                "input_type": "url",
                "required": True,
                "description": "URL to display",
                "value": "https://example.com"
            }
        ])

    def on_process(self, binder, user_id):
        url = self.property_value("url")
        output = OutputStatement(user_id)
        binder.append_node(PreviewNode(url))
        binder.post_message(output)
        return super().on_process(binder, user_id)


class PromptText(PromptBlock):
    def on_descriptor(self):
        return {
            "name": "Text",
            "summary": "No description available",
            "category": "prompt"
        }

    def load_template(self):
        super().load_template()
        self.append_template_properties([
            {
                "text": "Text Primary",
                "name": "primary_text",
                "format": "array",
                "input_type": "text",
                "required": True,
                "description": "List of strings to display",
                "value": []
            }
        ])

    def on_process(self, binder, user_id):
        output = OutputStatement(user_id)
        display_text = self._get_display_text()
        output.append_text(text=display_text)
        binder.post_message(output)
        return super().on_process(binder, user_id)

    def _get_display_text(self):
        primary_text = self.property_value("primary_text")
        pattern = random.choice(primary_text)
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
            "summary": "This block terminates the workflow.",
            "category": "terminal",
        }

    def on_process(self, binder, user_id):
        return self.move()

    def load_template(self):
        self.append_template_properties(
            [
                {
                    "text": "Post Action",
                    "name": "action",
                    "format": "enum",
                    "input_type": "select",
                    "required": True,
                    "description": "Action to execute after",
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

    @property
    def post_skill(self):
        return self.property_value("post_skill")
