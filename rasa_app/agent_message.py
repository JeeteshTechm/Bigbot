from rasa.core.agent import Agent
# from rasa.core.interpreter import RasaNLUInterpreter
from rasa.utils.endpoints import EndpointConfig
import asyncio

class Bot:
    def __init__(self, model_path, endpoint_url,sender_id):
        # interpreter = RasaNLUInterpreter(model_path)
        endpoint = EndpointConfig(url=endpoint_url)
        self.agent = Agent.load(model_path, action_endpoint=endpoint)
        self.sender_id="ab1"

    async def get_response(self, user_message):
        # message = UserMessage()
        tracker = self.agent.create_tracker("unique_sender_id")
        response = await self.agent.handle_message(user_message, tracker)
        print("+++++++",response)
        intent = response.get_intent_of_latest_message()
        confidence = response.get_confidence_of_latest_message()

        text = response.response[0]['text']
        result = {'text': text, 'intent': intent, 'confidence': confidence, 'response': response}
        return result
    

async def main():
    endpoint_url = "http://localhost:5055/webhook"  # replace with your endpoint URL
    bot = Bot("form_bot/models", endpoint_url,"ab1")
    response = await bot.get_response("book a table")
    print(response)

asyncio.run(main())
