from rasa.core.agent import Agent
from rasa.utils.endpoints import EndpointConfig
from rasa.core.tracker_store import SQLTrackerStore,InMemoryTrackerStore
from rasa.shared.core.domain import Domain
from rasa.core.tracker_store import DialogueStateTracker
import asyncio

class Bot:
    def __init__(self, model_path,sender_id):
   
        self.agent = Agent.load(model_path)

    async def get_response(self, user_message, sender_id):
        agent=Agent.load("./models")
        parsed = await self.agent.parse_message(user_message)
        intent = parsed['intent']['name']
        confidence = parsed['intent']['confidence']
        response = await self.agent.handle_text(user_message,sender_id=sender_id)
        result = {'text': response, 'intent': parsed}
    
        return result

async def main():
    sender_id = "sandeep"
    input_message="Book restaurant" # this parameter will be dynamic
    bot=Bot("./models",sender_id)
    response = await bot.get_response(input_message, sender_id)
    print(response)
    
    # based on skill classification agent will handshake with identified skill
    # Need to add futher script for above explanination
   
asyncio.run(main())
