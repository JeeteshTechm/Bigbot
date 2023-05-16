import yaml
import json

class YAMLToJsonConverter:
    def __init__(self, yaml_file_path, json_file_path):
        self.yaml_file_path = yaml_file_path
        self.json_file_path = json_file_path
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

            response_prefix = 'utter_' + intent_name
            for response_key, response_value in self.yaml_content['responses'].items():
                if response_key.startswith(response_prefix):
                    if isinstance(response_value, list):
                        for response in response_value:
                            intent['responses'].append(response['text'])
                    elif isinstance(response_value, dict):
                        intent['responses'].append(response_value['text'])

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
                intent['utterances'].append(example.strip())

            self.json_data['intents'].append(intent)

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
                        intent_data['slots'].append(slot)

                    break

    def convert_to_json(self):
        self.load_yaml()
        self.process_intents()
        self.process_forms()

        json_string = json.dumps(self.json_data, indent=4)

        with open(self.json_file_path, 'w') as file:
            file.write(json_string)


converter = YAMLToJsonConverter('sindalah.yml', 'sindalah.json')
converter.convert_to_json()
