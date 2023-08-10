import yaml
import json
import os
import uuid  

class YAMLToJsonConverter:
    def __init__(self, payload):
        self.yaml_content = payload
        self.json_data = {
            "bot_id":str(uuid.uuid4()),
            "intents": []
        }
    def process_intents(self):
        intent_to_story_action_map = {}

        # Populate the dictionary with the intent-to-story-action mapping
        for story in self.yaml_content['stories']:
            story_name = story['story']
            for step in story['steps']:
                if 'intent' in step:
                    intent_name = step['intent']
                    if intent_name not in intent_to_story_action_map:
                        intent_to_story_action_map[intent_name] = {'story_name': story_name, 'actions': []}
                if 'action' in step and step['action']:
                    intent_to_story_action_map[intent_name]['actions'].append(step['action'])
       
        # Process intents and add the corresponding story_name and all actions from the story
        for intent_data in self.yaml_content['nlu']:
            intent_name = intent_data['intent']
            
            # Create the intent structure
            intent = {
                "intent": intent_name,
                "response": [],
                "utterances": [],
                "story_name": intent_to_story_action_map.get(intent_name, {}).get('story_name', None),
                "actions": intent_to_story_action_map.get(intent_name, {}).get('actions', [])
            }

            if intent_name in self.yaml_content['forms']:
                form_name = intent_name + '_form'
                slots = self.yaml_content['forms'][form_name]
                intent['form'] = form_name
                intent['slots'] = []

                for slot_name, slot_type in slots.items():
                    slot = {
                        "name": slot_name,
                        "type": slot_type[0]['type'] if isinstance(slot_type, list) else slot_type
                    }
                    intent['slots'].append(slot)

            for example in intent_data['examples'].strip().split('\n'):
                utterance = example.strip()
                if utterance.startswith('-'):
                    utterance = utterance[1:].strip()
                intent['utterances'].append(utterance)

            # Append the intent to the JSON data
            self.json_data['intents'].append(intent)

        # Process stories to map intents with responses and add forms
        for story in self.yaml_content['stories']:
            for step in story['steps']:
                if 'intent' in step:
                    intent_name = step['intent']
                if 'action' in step and step['action'].startswith('utter_'):
                    response_key = step['action']
                    if response_key in self.yaml_content['responses']:
                        response_value = self.yaml_content['responses'][response_key]
                        if isinstance(response_value, list):
                            for response in response_value:
                                # Find the intent in the existing JSON structure and append the response
                                for existing_intent in self.json_data['intents']:
                                    if existing_intent['intent'] == intent_name:
                                        existing_intent['response'].append(response['text'])
                                        break
                        elif isinstance(response_value, dict):
                            # Find the intent in the existing JSON structure and append the response
                            for existing_intent in json_data['intents']:
                                if existing_intent['intent'] == intent_name:
                                    existing_intent['response'].append(response_value['text'])
                                    break

    def process_forms(self):
        form_intent_list = []

        for story in self.yaml_content['stories']:
            intent_name = None
            form_name = None

            for step in story['steps']:
                if 'intent' in step:
                    intent_name = step['intent']
                if 'active_loop' in step:
                    active_loop = step['active_loop']
                    if active_loop in self.yaml_content['forms']:
                        form_name = active_loop
                        break

            if intent_name and form_name:
                form_intent_list.append((form_name, intent_name))

        for form, intent in form_intent_list:
            for intent_data in self.json_data['intents']:
                if intent_data['intent'] == intent:
                    intent_data['form'] = form
                    intent_data['slots'] = []

                    for slot_name, slot_type in self.yaml_content['forms'][form].items():
                        slot = {
                            "name": slot_name,
                            "type":"any"
                        }

                        if 'responses' in self.yaml_content and 'utter_ask_' + slot_name in self.yaml_content['responses']:
                            bot_ask_list = self.yaml_content['responses']['utter_ask_' + slot_name]
                            if isinstance(bot_ask_list, list) and len(bot_ask_list) > 0:
                                slot['bot_ask'] = bot_ask_list[0]['text']
                                slot['examples']=[]
   
                        intent_data['slots'].append(slot)
                        intent_data['api_call'] = {
                                "method": "",
                                "url": "",
                                "request_body": []
                            }

                    break
        for story in self.yaml_content['stories']:
            for step in story['steps']:
                if 'slot_was_set' in step:
                    slot_was_set = step['slot_was_set']
                    for slot in slot_was_set:
                        for slot_name, slot_value in slot.items():
                            for intent in self.json_data['intents']:
                                if "slots" in intent:
                                    for slot_info in intent['slots']:
                                        if slot_info['name'] == slot_name:
                                            # Initialize 'examples' if it doesn't exist
                                            if 'examples' not in slot_info:
                                                slot_info['examples'] = []
                                            slot_info['examples'].append(slot_value)


    def add_ids_and_relations(self):
        intents = self.json_data['intents']
        num_intents = len(intents)

        # Add IDs to intents
        for i in range(num_intents):
            intent = intents[i]
            intent_id = 'id_' + str(i+1)
            intent['id'] = intent_id

        # Add parent and child IDs
        for i in range(num_intents - 1):
            intent = intents[i]
            intent['child_id'] = intents[i+1]['id']
        
        for i in range(1, num_intents):
            intent = intents[i]
            intent['parent_id'] = intents[i-1]['id']

    def convert_to_json(self):
        self.process_intents()
        self.process_forms()
        self.add_ids_and_relations()

        json_string = json.dumps(self.json_data, indent=4)

        return json_string

 
#with open("input/sindalah1.yml", 'r') as file:
    #yaml_content = yaml.safe_load(file)

#yaml_converter = YAMLToJsonConverter(yaml_content)
#json_data = yaml_converter.convert_to_json()
#print(json_data)
