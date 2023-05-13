import yaml
import json
import os
import glob
import uuid

class YamlToJsonConverter:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = None

    def load_yaml(self):
        with open(self.file_path, 'r') as file:
            self.data = yaml.safe_load(file)

    def process_intents(self):
        intents = self.data.get('nlu', [])
        intent_data = {}
        for intent in intents:
            intent_name = intent.get('intent', '')
            examples = intent.get('examples', '').split('\n')[1:]
            examples = [example.strip() for example in examples if example.strip()]
            intent_data[intent_name] = examples
        return intent_data

    def process_responses(self):
        responses = self.data.get('responses', {})
        response_data = {}
        for key, value in responses.items():
            response_key = key.split('_')[-1]
            response_data[response_key] = value[0]['text']
        return response_data

    def process_rules_and_stories(self):
        json_objects = {}

        for key in ['rules', 'stories']:
            if key in self.data:
                for item in self.data[key]:
                    steps = item['steps']
                    if steps:
                        intents = []
                        actions = []

                        for step in steps:
                            if "intent" in step:
                                intents.append(step["intent"])
                            if "action" in step:
                                actions.append(step["action"])

                        for intent in intents:
                            processed_json = {
                                "name": intent,
                                "actions": actions,
                            }
                            json_objects[processed_json['name']] = processed_json

        return json_objects

    def process_form_slots(self, actions):
        form_slots = []
        for action in actions:
            if action.startswith('action_ask'):
                slot_name = action.split('_')[-1]
                slot = {
                    "name": slot_name,
                    "type": "text"
                }
                form_slots.append(slot)
        return form_slots

    def process_forms(self):
        forms = self.data.get('forms', {})
        form_data = {}
        for key, value in forms.items():
            form_data[key] = value
        return form_data

    def process_slots(self):
        slots = self.data.get('slots', {})
        slot_data = {}
        for key, value in slots.items():
            slot_data[key] = value
        return slot_data

    def process_custom_actions(self, actions):
        custom_actions = [action for action in actions if not action.startswith(('utter', 'action_ask'))]
        return custom_actions

    def process_config(self):
        config = self.data.get('config', {})
        return config
    
    def convert_to_json(self, output_file):
        intents = self.process_intents()
        responses = self.process_responses()
        rules_and_stories = self.process_rules_and_stories()
        forms = self.process_forms()
        slots = self.process_slots()
        json_objects = []

        for i, (key, value) in enumerate(rules_and_stories.items()):  
            actions = [action for action in value['actions'] if not action.startswith('utter')]
            form_slots = self.process_form_slots(actions)
            custom_actions = self.process_custom_actions(actions)

            utterances= intents.get(key, [])
            utterances = [utterance.replace("-", "") for utterance in intents.get(key, [])]

            parent_intent_id = f"id_{i-1}" if i > 0 else -1
            child_intent_id = f"id_{i+1}" if i < len(rules_and_stories) - 1 else ""

            json_object = {
                "id": f"id_{len(json_objects)}",
                "name": key,
                "utterances": utterances,
                "responses": [responses.get(action.split('_')[-1], '') for action in value['actions'] if action.startswith('utter')],
                "parent_intent_id": parent_intent_id,
                "child_intent_id": child_intent_id
            }
            entities = [{"name": slot["name"], "value": ""} for slot in form_slots] 
            api_call={"method":" ", "URL":" ","request_body":" "}
        
            if form_slots:
                json_object["form"] = {
                    "name": key + "_form",
                    "slots": form_slots,
                    "entities":entities,
                    "api_call":api_call
                }

            json_objects.append(json_object)

        json_data = {"intents": json_objects}

        json_str = json.dumps(json_data, indent=2)
        

        with open(output_file, 'w') as file:
            file.write(json_str)

        return json_str


def main():
    input_dir = 'input'
    output_dir = 'output'

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    input_files = glob.glob(os.path.join(input_dir, '*.yml'))

    for idx, input_file in enumerate(input_files):
        output_file = os.path.join(output_dir, f'converted_bigbot_data_{idx:03d}.json')
        converter = YamlToJsonConverter(input_file)
        converter.load_yaml()
        json_str = converter.convert_to_json(output_file)


if __name__ == "__main__":
    main()
