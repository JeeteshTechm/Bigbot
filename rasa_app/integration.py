from rasa.core.agent import Agent
from rasa.utils.endpoints import EndpointConfig
from rasa.core.tracker_store import SQLTrackerStore,InMemoryTrackerStore
from rasa.shared.core.domain import Domain
from rasa.core.tracker_store import DialogueStateTracker
import asyncio

class Bot:

    async def get_response(self, user_message):
        agent=Agent.load("./models")
        parsed = await agent.parse_message(user_message)
        print("___________________",parsed["text"])
        skill_id=parsed["intent"]["name"]
        print(skill_id)
        bot=Bot()
        sender_id = "sandeep"
        conv_response= await bot.get_conversation(skill_id,user_message,sender_id)

        # result = { 'intent': parsed} 
        return conv_response

    async def get_conversation(self,skill_id, user_message, sender_id):
        tracker_store = SQLTrackerStore(
                dialect="postgresql",
                host="127.0.0.1",
                port="5432",
                username="rasa",
                password="rasa123",
                db="rasadb"
                )
        endpoint = "http://37.224.68.171:5055/webhook"
        model_path= skill_id + "/models"
        domain=skill_id + "/domain.yml"
        agent1 = Agent.load(model_path, action_endpoint=endpoint, tracker_store=tracker_store, domain=domain)
        parsed = await agent1.parse_message(user_message)
        intent = parsed['intent']['name']
        confidence = parsed['intent']['confidence']
        response = await agent1.handle_text(user_message,sender_id=sender_id)
        result = {'text': response, 'intent': parsed}
    
        return result



async def main():
    
    input_message="Book table"
    bot=Bot()
    response = await bot.get_response(input_message)
    print(response)
    
   
asyncio.run(main())
