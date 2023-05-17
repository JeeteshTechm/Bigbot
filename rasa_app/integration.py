from rasa.core.agent import Agent
from rasa.utils.endpoints import EndpointConfig
from rasa.core.tracker_store import SQLTrackerStore,InMemoryTrackerStore
from rasa.shared.core.domain import Domain
from rasa.core.tracker_store import DialogueStateTracker
import asyncio

class skill:
    async def get_response(self, user_message):
        agent=Agent.load("Skill_finder/models")
        parsed = await agent.parse_message(user_message)
        print("___________________",parsed["text"])
        skill_id=parsed["intent"]["name"]
        print(type(skill_id))
        # skill_id="book_restaurant"
         
        return skill_id




class Bot:
    def __init__(self, model_path, endpoint_url, domain,sender_id):
        endpoint = EndpointConfig(url=endpoint_url)
        tracker_store = SQLTrackerStore(
                dialect="postgresql",
                host="127.0.0.1",
                port="5432",
                username="rasa",
                password="rasa123",
                db="rasadb"
                )
        #tracker_store = InMemoryTrackerStore(max_event_history=10, domain=domain,sender_id=sender_id)
        self.agent = Agent.load(model_path, action_endpoint=endpoint, tracker_store=tracker_store, domain=domain)

    async def get_conv(self, user_message, sender_id):
        parsed = await self.agent.parse_message(user_message)
        # intent = parsed['intent']['name']
        # confidence = parsed['intent']['confidence']
        response = await self.agent.handle_text(user_message,sender_id=sender_id)
        print("____________________",response)
        print("-------------------",parsed)
        result = {'text': response, 'intent': parsed}
       
    
        return result

async def main():
    sk=skill()
    user_message="book table"
    
    endpoint_url = "http://37.224.68.171:5055/webhook"
    sender_id = "san"
    skill_id= await sk.get_response(user_message)
    print(skill_id)
    domain = Domain.load(skill_id+"/domain.yml")
    bot = Bot(skill_id+"/models", endpoint_url, domain,sender_id)
    response = await bot.get_conv(user_message, sender_id)
    print("_______-------------------",response)

asyncio.run(main())
