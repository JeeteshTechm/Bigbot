import yaml
import json
import os
import glob
import logging
import secrets
import re

logging.basicConfig(level=logging.INFO)

class YamlToJsonConverter:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = self.load_yaml()

    def load_yaml(self):
        if not os.path.exists(self.file_path):
            logging.error(f"File {self.file_path} does not exist.")
            return {}

        try:
            with open(self.file_path, 'r') as file:
                data = yaml.safe_load(file)
                return data if isinstance(data, dict) else {}
        except IOError as e:
            logging.error(f"Error opening file: {e}")
        except yaml.YAMLError as e:
            logging.error(f"Error parsing YAML file: {e}")
        
        return {}

    def process_intents(self):
        intents = {}
        for intent in self.data.get('nlu', []):
            name = intent.get('intent', '')
            examples = [ex.strip('- ') for ex in intent.get('examples', '').split('\n') if ex.strip()]
            intents[name] = {
                "examples": examples,
                "entities": self.extract_entities(examples)
            }
        return intents

    @staticmethod
    def extract_entities(examples):
        entities = []
        for ex in examples:
            entities += re.findall(r'\[([^]]+)\]\(([A-Za-z0-9_]+)\)', ex)
        return [{"entity": e[1], "value": e[0]} for e in entities]

    def process_responses(self):
        responses = {}
        for key, value in self.data.get('responses', {}).items():
            response_name = key.split('_')[-1]
            responses[response_name] = [resp_dict['text'] for resp_dict in value]
        return responses

    def process_slots(self):
        return self.data.get('slots', {})

    def process_rules_and_stories(self):
        json_objects = []
        for key in ['rules', 'stories']:
            for item in self.data.get(key, []):
                steps = item.get('steps', [])
                # Preserve the original order of the items
                steps_processed = []
                utterances = []
                actions = []
                active_loops = []
                slot_was_set = []
                for step in steps:
                    if "intent" in step:
                        steps_processed.append({"intent": step.get("intent")})
                        utterances.append(step.get("intent"))
                    if "action" in step:
                        steps_processed.append({"action": step.get("action")})
                        actions.append(step.get("action"))
                    if "active_loop" in step and step.get("active_loop") is not None:
                        steps_processed.append({"active_loop": step.get("active_loop")})
                        active_loops.append(step.get("active_loop"))
                    if "slot_was_set" in step:
                        slot_was_set += step.get("slot_was_set")

                processed_json = {
                    "name": item.get('story', ''),
                    "steps": steps_processed,  # Use the processed steps
                    "utterances": utterances,  # Adding utterances here
                    "actions": actions,  # Adding actions here
                    "active_loops": active_loops,  # Adding active_loops here
                    "slot_was_set": slot_was_set,  # Adding slot_was_set here
                    "api_calls": None,  # Adding api_calls here
                    "form_responses": None,  # Adding form_responses here
                }
                json_objects.append(processed_json)

        return json_objects



    def convert_to_json(self):
        intents = self.process_intents()
        responses = self.process_responses()
        rules_and_stories = self.process_rules_and_stories()
        slots = self.process_slots()

        ids = [secrets.token_hex(5) for _ in range(len(rules_and_stories))]

        json_objects = [{
            "id": id,
            "name": item['name'],
            "utterances": [intents.get(intent, {"examples": [], "entities": []}) for intent in item['utterances']],
            "responses": [responses.get(action.split('_')[-1], '') for action in item['actions'] if action.startswith('utter')],
            "form_responses": [responses.get(action.split('_')[-1], '') for action in item['active_loops'] if action and action.endswith('_form')],
            "actions": [action for action in item['actions'] if not action.startswith(('utter', 'action_ask'))],
            "active_loops": item.get('active_loops', []),
            "slot_was_set": item.get('slot_was_set', []),        
            "slots": slots,
            "parent_id": ids[idx-1] if idx > 0 else "-1",
            "child_id": ids[idx+1] if idx < len(rules_and_stories) - 1 else "-1",
            "api_calls": item.get('api_calls'),
            "form_responses": item.get('form_responses'),  # Ensure form_responses is included in output
        } for idx, (item, id) in enumerate(zip(rules_and_stories, ids))]

        json_str = json.dumps(json_objects, indent=2)

        return json_str

    def save_json(self, file_path, json_str):
        try:
            with open(file_path, 'w') as file:
                file.write(json_str)
        except IOError as e:
            logging.error(f"Error writing to file: {e}")


def main():
    input_dir = 'input'
    output_dir = 'rasa_training_files'

    os.makedirs(output_dir, exist_ok=True)

    input_files = glob.glob(os.path.join(input_dir, '*.yml'))

    for idx, input_file in enumerate(input_files):
        output_file = os.path.join(output_dir, f'converted_bigbot_data_{idx:03d}.json')
        converter = YamlToJsonConverter(input_file)
        if converter.data:
            json_str = converter.convert_to_json()
            converter.save_json(output_file, json_str)


if __name__ == "__main__":
    main()