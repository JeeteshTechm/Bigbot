from rasa.core.agent import Agent
from rasa.utils.endpoints import EndpointConfig
from rasa.core.tracker_store import SQLTrackerStore
from rasa.shared.core.domain import Domain
import asyncio

class Bot:
    def __init__(self, model_path, endpoint_url, domain):
        endpoint = EndpointConfig(url=endpoint_url)
        tracker_store = SQLTrackerStore(
            dialect="postgresql",
            url="37.224.68.171",
            db="rasa_safana",
            username="bigbot",
            password="safana2023",
            event_broker=None,
            event_broker_url=None,
            event_broker_username=None,
            event_broker_password=None,
        )
        self.agent = Agent.load(model_path, action_endpoint=endpoint, tracker_store=tracker_store, domain=domain)

    async def get_response(self, user_message, sender_id):
        parsed = await self.agent.parse_message(user_message)
        intent = parsed['intent']['name']
        confidence = parsed['intent']['confidence']
        response = await self.agent.handle_text(user_message, sender_id=sender_id)
        result = {'text': response, 'intent': parsed}
    
        return result

async def main():
    domain = Domain.load("latest/domain.yml")
    endpoint_url = "http://localhost:5055/webhook"
    bot = Bot("latest/models", endpoint_url, domain)
    sender_id = "123"
    response = await bot.get_response("book a table", sender_id)
    print(response)
    
   
asyncio.run(main())
