"""This module must be a perfect copy of the equivalent module in the the customer repo."""

import json

from .Node import BaseNode, TextNode, PaymentNode


class InputStatement:
    def __init__(self, user_id, **kwargs):
        self.user_id = user_id
        self.text = kwargs.get("text")
        self.input = kwargs.get("input")
        self.flag = kwargs.get("flag, None")

    def __str__(self):
        return self.text if self.text else super().__str__()

    def get_node(self):
        return BaseNode.deserialize(self.input)


class OutputStatement:
    """A statement represents a single spoken entity, sentence or phrase that someone can say."""

    def __init__(self, user_id, **kwargs):
        self.user_id = user_id
        self.confidence = kwargs.get("confidence", None)
        self.contents = []

    def __str__(self):
        for item in self.contents:
            if isinstance(item, TextNode):
                return item.data
            elif isinstance(item, PaymentNode):
                meta = item.get_meta()
                if meta and meta.get("payment_services"):
                    name = meta.get("payment_services")[0]["name"]
                    payment_url = meta.get("payment_services")[0]["payment_url"]
                    return f"This is payment node: {name} - {payment_url}"
        return super().__str__()

    def append_node(self, node):
        self.contents.append(node)

    def append_text(self, text):
        self.contents.append(TextNode(text))

    def serialize(self):
        """Returns a dictionary representation of the statement."""
        return {
            "confidence": self.confidence,
            "contents": self.contents,
            "user_id": self.user_id,
        }
