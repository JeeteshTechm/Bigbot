import requests

from main import Node as node
from main.Component import DataExchange
from main.Statement import OutputStatement


class GetRandomImage(DataExchange):
    def call(self, binder, operator_id, package, data, **kwargs):
        response = requests.get("https://picsum.photos/500")

        output = OutputStatement(operator_id)
        output.append_text("Image retrieved:")
        output.append_node(node.ImageNode(response.url))
        binder.post_message(output)

        return {"random_image": response.url}
