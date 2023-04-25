from rasa.core.agent import Agent
from rasa.utils.endpoints import EndpointConfig
from rasa.core.tracker_store import SQLTrackerStore
from rasa.shared.core.domain import Domain
import asyncio
import json

class Bot:
    def __init__(self, config):
        model_path = config["model_path"]
        endpoint_url = config["endpoint_url"]
        domain = Domain.load(config["domain_path"])

        tracker_store_config = config["tracker_store"]
        tracker_store = SQLTrackerStore(
            dialect=tracker_store_config["dialect"],
            url=tracker_store_config["url"],
            db=tracker_store_config["db"],
            username=tracker_store_config["username"],
            password=tracker_store_config["password"],
            event_broker=None,
            event_broker_url=None,
            event_broker_username=None,
            event_broker_password=None,
        )

        endpoint = EndpointConfig(url=endpoint_url)
        self.agent = Agent.load(model_path, action_endpoint=endpoint, tracker_store=tracker_store, domain=domain)

    async def get_response(self, user_message, sender_id):
        parsed = await self.agent.parse_message(user_message)
        intent = parsed['intent']['name']
        confidence = parsed['intent']['confidence']
        response = await self.agent.handle_text(user_message, sender_id=sender_id)
        result = {'text': response, 'intent': parsed}

        return result

async def main():
    with open("rasa_agent_config.json") as config_file:
        config = json.load(config_file)

    bot = Bot(config)
    sender_id = "123"
    response = await bot.get_response("book a table", sender_id)
    print(response)

asyncio.run(main())
