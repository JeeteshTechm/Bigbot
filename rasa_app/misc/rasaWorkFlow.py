import rasa
from rasa.core.agent import Agent
import asyncio
from rasa.core.http_interpreter import RasaNLUHttpInterpreter
# from rasa.shared.core.training_data.story_reader.story_reader.StoryReader import StoryReader

def get_next_action(story_path: str, model_path: str) -> str:
    agent = Agent.load(model_path)
    response=agent.parse_message({"message_data":"hi"})
    print(response)
    
    story = rasa.shared.core.training_data.story_reader.StoryReader.read_from_file(story_path)
    tracker = rasa.shared.core.events.deserializer.create_tracker_from_dialogue_events(story.events, agent.domain.slots)

    next_action = agent.predict_next_action(tracker)

    return next_action.name()

interpreter = RasaNLUHttpInterpreter(endpoint_config=None)
async def process_message():
    response = await interpreter.parse(text="hi")
    return response
response = asyncio.run(process_message())
story_path=".\data\nlu.yml"
model_path=".\models"
print(get_next_action(story_path,model_path))
print(response)




