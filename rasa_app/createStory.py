import json
import yaml
from collections import OrderedDict


def generate_stories_json(json_string):
    bot_data = json.loads(json_string)
    
    stories = []
    for intent in bot_data['intents']:
        for i, utterance in enumerate(intent['utterances']):
            story = f"\n## {intent['name']} {i+1}"
            story += f"\n- {utterance}"
            
            story += f"\n  - {intent['responses'][i]}"
            
            if 'child_id' in intent:
                child_id = intent['child_id']
                
                while child_id != '+1':
                    child_intent = next(child for child in bot_data['intents'] if child['id'] == child_id)
                    story += f"\n- {child_intent['utterances'][0]}"
                    child_id = child_intent['child_id']
                goodbye_intent = next(child for child in bot_data['intents'] if child['id'] == '+1')
                story += f"\n  - {goodbye_intent['responses'][i]}"
            
            stories.append(story)
    stories_string = "\n".join(stories)
    return stories_string


with open('payload4.json', 'r') as f:
    data = json.load(f,object_pairs_hook=OrderedDict)
new_data=generate_stories_json(data)
yaml_data = yaml.dump(new_data)
with open('stories2.yml', 'w') as yaml_file:
    yaml_file.write(yaml_data)
