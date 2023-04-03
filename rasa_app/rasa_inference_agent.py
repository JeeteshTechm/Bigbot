import asyncio
from rasa.core.agent import Agent

class Bot:
    def __init__(self, model_path):
        self.model_path = model_path
        self.agent = Agent.load(self.model_path)

    async def get_response(self, user_message):
        # Use the agent to parse the user message and get a response
        parsed = await self.agent.parse_message(user_message)
        intent = parsed['intent']['name']
        confidence = parsed['intent']['confidence']
        response = await self.agent.handle_text(user_message)

        # Extract the text of the first response and add intent and confidence
        text = response[0]['text']
        result = {'text': text, 'intent': intent, 'confidence': confidence}
        return result

    
async def main():
    # Create a Bot instance and pass in the path to the Rasa model
    bot = Bot("concertbot/models")

    # Call the get_response() method using the await keyword
    response = await bot.get_response("hi")
    print(response)

# Run the main function using asyncio
asyncio.run(main())
