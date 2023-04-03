import asyncio
from rasa.core.agent import Agent

class Bot:
    def __init__(self, model_path):
        self.model_path = model_path
        self.agent = Agent.load(self.model_path)

    async def get_response(self, user_message):
        parsed = await self.agent.parse_message(user_message)
        intent = parsed['intent']['name']
        confidence = parsed['intent']['confidence']
        response = await self.agent.handle_text(user_message)

        text = response[0]['text']
        result = {'text': text, 'intent': intent, 'confidence': confidence}
        return result

    
async def main():
    bot = Bot("concertbot/models")
    response = await bot.get_response("hi")
    print(response)

asyncio.run(main())
