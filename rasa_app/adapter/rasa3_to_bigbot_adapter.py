import yaml
import json
import os

class YAMLToJsonConverter:
    def __init__(self, yaml_file_path):
        self.yaml_file_path = yaml_file_path
        self.yaml_content = None
        self.json_data = {
            "intents": []
        }

    def load_yaml(self):
        with open(self.yaml_file_path, 'r') as file:
            self.yaml_content = yaml.safe_load(file)

    def process_intents(self):
        for intent_data in self.yaml_content['nlu']:
            intent_name = intent_data['intent']
            intent = {
                "name": intent_name,
                "responses": [],
                "utterances": []
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
                                    if existing_intent['name'] == intent_name:
                                        existing_intent['responses'].append(response['text'])
                                        break
                        elif isinstance(response_value, dict):
                            # Find the intent in the existing JSON structure and append the response
                            for existing_intent in json_data['intents']:
                                if existing_intent['name'] == intent_name:
                                    existing_intent['responses'].append(response_value['text'])
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
                if intent_data['name'] == intent:
                    intent_data['form'] = form
                    intent_data['slots'] = []

                    for slot_name, slot_type in self.yaml_content['forms'][form].items():
                        slot = {
                            "name": slot_name,
                            "type": slot_type[0]['type'] if isinstance(slot_type, list) else slot_type
                        }

                        if 'responses' in self.yaml_content and 'utter_ask_' + slot_name in self.yaml_content['responses']:
                            bot_ask_list = self.yaml_content['responses']['utter_ask_' + slot_name]
                            if isinstance(bot_ask_list, list) and len(bot_ask_list) > 0:
                                slot['bot_ask'] = bot_ask_list[0]['text']
                                slot['examples']=[]
   
                        intent_data['slots'].append(slot)
                        intent_data['api_call'] = {
                                "method": "",
                                "URL": "",
                                "request_body": []
                            }

                    break
        for story in self.yaml_content['stories']:
            for step in story['steps']:
                #print(step)
                if 'slot_was_set' in step:
                    slot_was_set = step['slot_was_set']
                    for slot in slot_was_set:
                        for slot_name, slot_value in slot.items():
                            for intent in self.json_data['intents']:
                                if "slots" in intent:
                                    for slot_info in intent['slots']:
                                        if slot_info['name'] == slot_name:
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
        self.load_yaml()
        self.process_intents()
        self.process_forms()
        self.add_ids_and_relations()

        json_string = json.dumps(self.json_data, indent=4)

        output_file = os.path.splitext(self.yaml_file_path)[0] + ".json"

        with open(output_file, "w") as file:
            file.write(json_string)

    
#yaml_converter = YAMLToJsonConverter("input/sindalah.yml")
#json_data = yaml_converter.convert_to_json()
