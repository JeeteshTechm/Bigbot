from rasa.core.agent import Agent
from rasa.core.interpreter import RasaNLUInterpreter
from rasa.utils.endpoints import EndpointConfig
import asyncio

class Bot:
    def __init__(self, model_path, endpoint_url):
        interpreter = RasaNLUInterpreter(model_path)
        endpoint = EndpointConfig(url=endpoint_url)
        self.agent = Agent.load(model_path, interpreter=interpreter, action_endpoint=endpoint)

    async def get_response(self, user_message):
        parsed = await self.agent.parse_message(user_message)
        intent = parsed['intent']['name']
        confidence = parsed['intent']['confidence']
        response = await self.agent.handle_text(user_message)

        text = response[0]['text']
        result = {'text': text, 'intent': intent, 'confidence': confidence}
        return result

async def main():
    endpoint_url = "http://localhost:5055/webhook"  # replace with your endpoint URL
    bot = Bot("path/to/nlu/model", endpoint_url)
    response = await bot.get_response("hi")
    print(response)

asyncio.run(main())
