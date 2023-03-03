import json

from .Node import BaseNode, TextNode, PaymentNode


class InputStatement:
    def __init__(self, user_id, text=None, input=None, flag=None):
        self.user_id = user_id
        self.text = text
        self.input = input
        self.flag = flag

    def __str__(self):
        return self.text if self.text else super().__str__()

    def get_node(self):
        try:
            return BaseNode.deserialize(self.input)
        except Exception as e:
            raise ValueError(f"Failed to deserialize input: {e}")

    def validate(self):
        if not self.input:
            raise ValueError("Input is required")

class OutputStatement:
    """A statement represents a single spoken entity, sentence or phrase that someone can say."""

    def __init__(self, user_id, confidence=None):
        self.user_id = user_id
        self.confidence = confidence
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

    def validate(self):
        if not self.contents:
            raise ValueError("Output contents are required")

    @classmethod
    def from_dict(cls, data):
        statement = cls(data.get("user_id"), data.get("confidence"))
        for node_dict in data.get("contents", []):
            if node_dict.get("type") == "text":
                statement.append_text(node_dict.get("data"))
            elif node_dict.get("type") == "payment":
                node = PaymentNode(node_dict.get("amount"), node_dict.get("currency"))
                node.set_meta(node_dict.get("meta"))
                statement.append_node(node)
        return statement

    def to_dict(self):
        contents = []
        for item in self.contents:
            if isinstance(item, TextNode):
                node_dict = {"type": "text", "data": item.data}
            elif isinstance(item, PaymentNode):
                node_dict = {
                    "type": "payment",
                    "amount": item.amount,
                    "currency": item.currency,
                    "meta": item.get_meta(),
                }
            contents.append(node_dict)
        return {"user_id": self.user_id, "confidence": self.confidence, "contents": contents}
