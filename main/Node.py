"""This module must be a perfect copy of the equivalent module in the the customer repo."""
import json
from jinja2 import Template

# Define a function to return serialized data for all node types
def all():
    serialized_data = []
    for node_type in NODE_TYPES:
        node = node_type(None, None)
        serialized_data.append(node.serialize())
    return serialized_data


# Define the base class for all nodes
class BaseNode:
    def __init__(self, node, data, meta):
        self.node = node
        self.data = data
        self.meta = meta

    def get_data(self):
        return self.data

    def get_meta(self):
        return self.meta

    def serialize(self):
        return {
            "node": self.node,
            "data": self.data,
            "meta": self.meta,
        }

    @staticmethod
    def deserialize(object):
        if isinstance(object, dict):
            node = object.get("node")
            data = object.get("data")
            meta = object.get("meta")
            if node == "big.bot.core.audio":
                return AudioNode(data, meta)
            elif node == "big.bot.core.binary":
                return BinaryNode(data, meta)
            elif node == "big.bot.core.cancel":
                return CancelNode(data, meta)
            elif node == "big.bot.core.delegates":
                return DelegatesNode(data, meta)
            elif node == "big.bot.core.iframe":
                return IFrameNode(data, meta)
            elif node == "big.bot.core.image":
                return ImageNode(data, meta)
            elif node == "big.bot.core.notification":
                return NotificationNode(data, meta)
            elif node == "big.bot.core.oauth":
                return OAuthNode(data, node)
            elif node == "big.bot.core.payment":
                return PaymentNode(data, meta)
            elif node == "big.bot.core.picker.date":
                return DateNode(data, meta)
            elif node == "big.bot.core.picker.datetime":
                return DateTimeNode(date, meta)
            elif node == "big.bot.core.picker.duration":
                return DurationNode(data, meta)
            elif node == "big.bot.core.picker.file":
                return InputBinaryNode(data, meta)
            elif node == "big.bot.core.preview":
                return PreviewNode(data, meta)
            elif node == "big.bot.core.search":
                return SearchNode(data, meta)
            elif node == "big.bot.core.skip":
                return SkipNode(data, meta)
            elif node == "big.bot.core.text":
                return TextNode(data, meta)
            else:
                raise ValueError(f"Invalid node type: {node}")


# Define a subclass of BaseNode for the "Audio" node type
class AudioNode(BaseNode):
    def __init__(self, data, meta=None):
        super().__init__("big.bot.core.audio", data, meta)


# Define a subclass of BaseNode for the "Binary" node type
class BinaryNode(BaseNode):
    def __init__(self, data, meta=None):
        super().__init__("big.bot.core.binary", data, meta)



class CancelNode(BaseNode):
    def __init__(self, data=None, meta=None):
        super().__init__("big.bot.core.cancel", data, meta)


class DateNode(BaseNode):
    def __init__(self, data=None, meta=None):
        super().__init__("big.bot.core.picker.date", data, meta)


class DateTimeNode(BaseNode):
    def __init__(self, data=None, meta=None):
        super().__init__("big.bot.core.picker.datetime", data, meta)


    """The DelegatesNode has the following structure:

    {
        "node": "big.bot.core.delegates",
        "data": [                                                   # List of delegates
            {
                "body": "Delegate Name",                            # Delegate's name
                "context": [2, 4],                                  # Delegate's contexts
                "image" "https://url.to.delegates.avatar.image",
                "values": [5, 27],                                  # Delegate's id and skill's id
            },
            ...
        ],
        "meta": None,
    }

    The context field can one of the following values:

    + [1] - Where 1 is CTX_HUMAN_DELEGATE_SELECT.
    + [2, 4] - Where 2 is CTX_BOT_DELEGATE_SELECT, and 4 is CTX_START_SKILL.

    There's to cases for the values field:

    + [5] - An array with a single integer in the case of HumanDelegates, the integer is the
      delegate's id.
    + [5, 27] - An array with two integers in the case of BotDelegates, the first integer is the
      delegate's id, the second integers is the skill's id.
    """
class DelegatesNode(BaseNode):
    def __init__(self, data=None, meta=None):
        super().__init__("big.bot.core.delegates", data, meta)


class DurationNode(BaseNode):
    def __init__(self, data=None, meta=None):
        super().__init__("big.bot.core.picker.duration", data, meta)


class IFrameNode(BaseNode):
    def __init__(self, data, meta=None):
        super().__init__("big.bot.core.iframe", data, meta)


class ImageNode(BaseNode):
    def __init__(self, data, meta=None):
        super().__init__("big.bot.core.image", data, meta)


    """The InputFileNode should have the following structure:
    {
        "node": "big.bot.core.picker.file",
        "data": None,
        "meta": {
            "accept": "image/*",
            "size": 1000000,
        },
    }
    Where:
        + accept: Accepted file extensions, can be any value accepted by the accept property of an
            HTML input tag.
        + size: Maximun size of the file in bytes.
    """
class InputFileNode(BaseNode):
    def __init__(self, meta=None):
        super().__init__("big.bot.core.picker.file", None, meta)


class NotificationNode(BaseNode):
    def __init__(self, data, meta=None):
        super().__init__("big.bot.core.notification", data, meta)


class OAuthNode(BaseNode):
    def __init__(self, data, meta=None):
        super().__init__("big.bot.core.oauth", data, meta)


    """Node to PreviewNode provides webpage previews for a given a URL, it has the following structure
    {
        "data": "<url>",
        "meta": {
            "summary": "URL's summary or descriptiom",
            "thumbnail": "URL's thumbnail",
            "title": "URL's title",
        },
    }
    """
class PreviewNode(BaseNode):
    def __init__(self, data, meta=None):
        try:
            from contrib.utils import web_preview

            title, summary, thumbnail = web_preview(data)
        except:
            title, summary, thumbnail = "", "", ""

        meta = meta or {}
        meta.update({
            "summary": meta.get("summary", summary),
            "thumbnail": meta.get("thumbnail", thumbnail),
            "title": meta.get("title", title),
        })

        super().__init__("big.bot.core.preview", data, meta)


class PaymentNode(BaseNode):
    def __init__(self, data, meta=None):
        meta = meta or {}
        meta.update({
            "charge_summary": meta.get("charge_summary", "You have to pay"),
            "currency_code": meta.get("currency_code", "USD"),
            "currency_symbol": meta.get("currency_symbol", "$"),
            "button_text": meta.get("button_text", "Make Payment"),
            "payment_services": meta.get("payment_services", [
                {
                    "name": "Bank Card",
                    "icon": "https://cdn.worldvectorlogo.com/logos/apple-pay.svg",
                    "payment_url": "https://razorpay.com/?version=t1",
                },
                {
                    "name": "Google Pay",
                    "icon": "https://cdn.worldvectorlogo.com/logos/apple-pay.svg",
                    "payment_url": "https://razorpay.com/?version=t1",
                },
                {
                    "name": "Apple Pay",
                    "icon": "https://cdn.worldvectorlogo.com/logos/apple-pay.svg",
                    "payment_url": "https://razorpay.com/?version=t1",
                },
            ]),
        })

        super().__init__("big.bot.core.payment", data, meta)



class SearchNode(BaseNode):
    NODE_TYPE = "big.bot.core.search"

    def __init__(self, data, meta=None):
        super().__init__(SearchNode.NODE_TYPE, data, meta)

    def __str__(self):
        node = self.get_node()
        if isinstance(node, CancelNode):
            return "Cancel"
        elif isinstance(node, SkipNode):
            return "Skip"
        elif isinstance(node, TextNode):
            return node.data
        return super().__str__()

    @staticmethod
    def wrap_text(display_text, input):
        return SearchNode(input, TextNode(display_text).serialize())

    @staticmethod
    def wrap_cancel():
        return SearchNode(None, CancelNode().serialize())

    @staticmethod
    def wrap_skip():
        return SearchNode(None, SkipNode().serialize())

    def get_node(self):
        return BaseNode.deserialize(self.get_meta())


class SkipNode(BaseNode):
    NODE_TYPE = "big.bot.core.skip"

    def __init__(self, data=None, meta=None):
        super().__init__(SkipNode.NODE_TYPE, data, meta)


class TextNode(BaseNode):
    NODE_TYPE = "big.bot.core.text"

    def __init__(self, data, meta=None):
        super().__init__(TextNode.NODE_TYPE, data, meta)


class TTSNode(BaseNode):
    NODE_TYPE = "big.bot.core.tts"

    def __init__(self, data, meta=None):
        super().__init__(TTSNode.NODE_TYPE, data, meta)



# Define a list of node types that can be set by the user
NODE_TYPES = [
    AudioNode,
    BinaryNode,
    DateNode,
    DateTimeNode,
    DurationNode,
    IFrameNode,
    ImageNode,
    InputFileNode,
    NotificationNode,
    OAuthNode,
    PaymentNode,
    PreviewNode,
    TextNode,
]
