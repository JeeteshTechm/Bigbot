"""This module must be a perfect copy of the equivalent module in the the customer repo."""

import json

from .Node import BaseNode, TextNode, PaymentNode


class InputStatement:
    def __init__(self, user_id, **kwargs):
        self.user_id = user_id
        self.text = kwargs.get("text")
        self.input = kwargs.get("input")
        self.flag = kwargs.get("flag")

    def __str__(self):
        if self.text:
            return self.text
        return super(InputStatement, self).__str__()

    def get_node(self):
        return BaseNode.deserialize(self.input)


class OutputStatement:
    """A statement represents a single spoken entity, sentence or phrase that someone can say."""

    def __init__(self, user_id, **kwargs):
        self.user_id = user_id
        self.confidence = kwargs.get("confidence")
        self.contents = []

    def __str__(self):
        for item in self.contents:
            if isinstance(item, TextNode):
                return item.data
            elif isinstance(item, PaymentNode):
                if item.get_meta().get("payment_services"):
                    name = item.get_meta().get("payment_services")[0]["name"]
                    payment_url = item.get_meta().get("payment_services")[0][
                        "payment_url"
                    ]
                    return "This is payment node : https://bit.ly/3mI35D7"
        return super(OutputStatement, self).__str__()

    def append_node(self, node):
        self.contents.append(node)

    def append_text(self, text):
        self.contents.append(TextNode(text))

    def serialize(self):
        """Returns a dictionary representation of the statement."""
        data = {
            "confidence": self.confidence,
            "contents": self.contents,
            "user_id": self.user_id,
        }
        return data
