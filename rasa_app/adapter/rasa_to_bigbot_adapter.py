import yaml
import json
import os
import glob
import logging
import secrets
import re
from typing import Dict, List, Tuple


logging.basicConfig(level=logging.INFO)


class YamlToJsonConverter:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data = self.load_yaml()

    def load_yaml(self) -> Dict:
        """Loads a YAML file and returns it as a dictionary."""
        if not os.path.exists(self.file_path):
            logging.error(f"File {self.file_path} does not exist.")
            return {}

        try:
            with open(self.file_path, 'r') as file:
                data = yaml.safe_load(file)
                return data if isinstance(data, dict) else {}
        except (IOError, yaml.YAMLError) as e:
            logging.error(f"Error opening or parsing YAML file: {e}")
            return {}

    def convert_to_json(self) -> str:
        """Converts the loaded YAML data to JSON."""
        if not self.data:
            return json.dumps([])

        intents = self.process_intents()
        responses = self.process_responses()
        slots = self.process_slots()
        stories = self.process_rules_and_stories()

        ids = [secrets.token_hex(5) for _ in range(len(stories))]
        json_data = [
            self.build_json_object(idx, story, id_, intents, responses, slots, len(stories), ids)
            for idx, (story, id_) in enumerate(zip(stories, ids))
        ]

        return json.dumps(json_data, indent=2)

    def save_json(self, file_path: str, json_str: str):
        """Saves the given JSON string to a file."""
        try:
            with open(file_path, 'w') as file:
                file.write(json_str)
        except IOError as e:
            logging.error(f"Error writing to file: {e}")

    def process_intents(self) -> Dict:
        """Processes the intents from the YAML data."""
        return {
            intent.get('intent', ''): {
                "examples": self.extract_examples(intent),
                "entities": self.extract_entities(intent)
            }
            for intent in self.data.get('nlu', [])
        }

    @staticmethod
    def extract_examples(intent: Dict) -> List[str]:
        """Extracts examples from an intent."""
        return [
            ex.strip('- ')
            for ex in intent.get('examples', '').split('\n')
            if ex.strip()
        ]

    @staticmethod
    def extract_entities(intent: Dict) -> List[Dict]:
        """Extracts entities from an intent."""
        entities = [
            re.findall(r'\[([^]]+)\]\(([A-Za-z0-9_]+)\)', ex)
            for ex in intent.get('examples', '').split('\n')
            if ex.strip()
        ]
        return [
            {"entity": e[1], "value": e[0]}
            for entity in entities for e in entity
        ]

    def process_responses(self) -> Dict:
        """Processes the responses from the YAML data."""
        return {
            response_key.split('_')[-1]: [resp_dict['text'] for resp_dict in value]
            for response_key, value in self.data.get('responses', {}).items()
        }

    def process_slots(self) -> Dict:
        """Processes the slots from the YAML data."""
        return self.data.get('slots', {})

    def process_rules_and_stories(self) -> List[Dict]:
        """Processes the rules and stories from the YAML data."""
        return [
            self.process_item(item)
            for key in ['rules', 'stories']
            for item in self.data.get(key, [])
        ]

    def process_item(self, item: Dict) -> Dict:
        """Processes a single item (rule or story)."""
        steps_processed, utterances, actions, active_loops, slot_was_set = self.process_steps(item)
        return {
            "name": item.get('story', ''),
            "steps": steps_processed, 
            "utterances": utterances,
            "actions": actions,
            "active_loops": active_loops,  
            "slot_was_set": slot_was_set,  
            "api_calls": None,  
            "form_responses": None,  
        }

    @staticmethod
    def process_steps(item: Dict) -> Tuple[List[Dict], List[str], List[str], List[str], List[str]]:
        """Processes the steps of an item."""
        steps_processed = []
        utterances = []
        actions = []
        active_loops = []
        slot_was_set = []
        for step in item.get('steps', []):
            steps_processed, utterances, actions, active_loops, slot_was_set = \
                YamlToJsonConverter.analyze_step(step, steps_processed, utterances, actions, active_loops, slot_was_set)
        return steps_processed, utterances, actions, active_loops, slot_was_set

    @staticmethod
    def analyze_step(step: Dict, steps_processed: List[Dict], utterances: List[str], actions: List[str],
                     active_loops: List[str], slot_was_set: List[str]) -> Tuple[List[Dict], List[str], List[str], List[str], List[str]]:
        """Analyzes a single step of an item."""
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
        return steps_processed, utterances, actions, active_loops, slot_was_set

    def build_json_object(self, idx: int, story: Dict, id_: str, intents: Dict, responses: Dict,
                          slots: Dict, total_stories: int, ids: List[str]) -> Dict:
        """Builds a JSON object for a single story."""
        return {
            "id": id_,
            "name": story['name'],
            "utterances": [intents.get(intent, {"examples": [], "entities": []}) for intent in story['utterances']],
            "responses": [responses.get(action.split('_')[-1], '') for action in story['actions'] if action.startswith('utter')],
            "form_responses": [responses.get(action.split('_')[-1], '') for action in story['active_loops'] if action and action.endswith('_form')],
            "actions": [action for action in story['actions'] if not action.startswith(('utter', 'action_ask'))],
            "active_loops": story.get('active_loops', []),
            "slot_was_set": story.get('slot_was_set', []),        
            "slots": slots,
            "parent_id": ids[idx-1] if idx > 0 else "-1",
            "child_id": ids[idx+1] if idx < total_stories - 1 else "-1",
            "api_calls": story.get('api_calls'),
            "form_responses": story.get('form_responses'),
        }

    def convert_to_json(self) -> str:
        """Converts the YAML data to JSON."""
        intents = self.process_intents()
        responses = self.process_responses()
        stories = self.process_rules_and_stories()
        slots = self.process_slots()

        ids = [secrets.token_hex(5) for _ in range(len(stories))]

        json_objects = [
            self.build_json_object(idx, story, id_, intents, responses, slots, len(stories), ids)
            for idx, (story, id_) in enumerate(zip(stories, ids))
        ]

        return json.dumps(json_objects, indent=2)

    @staticmethod
    def save_json(file_path: str, json_str: str):
        """Saves the JSON string to a file."""
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

