import yaml
import json
import os
import glob
import logging

logging.basicConfig(level=logging.INFO)

class JsonToYamlConverter:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = self.load_json()

    def load_json(self):
        if not os.path.exists(self.file_path):
            logging.error(f"File {self.file_path} does not exist.")
            return None

        try:
            with open(self.file_path, 'r') as file:
                return json.load(file)
        except (IOError, json.JSONDecodeError) as e:
            logging.error(f"Error opening or parsing JSON file: {e}")

    def convert_to_yaml(self):
        if not self.data:
            return None

        yaml_data = {
            'version': '3.0',
            'nlu': self.convert_nlu(),
            'responses': self.convert_responses(),
            'slots': self.convert_slots(),
            'stories': self.convert_stories(),
        }

        return yaml.dump(yaml_data, sort_keys=False, default_flow_style=False, allow_unicode=True)

    def convert_nlu(self):
        nlu = []
        for item in self.data:
            for utterance in item['utterances']:
                examples = utterance['examples']
                nlu.append({"intent": item['name'], "examples": examples})
        return nlu


    def convert_responses(self):
        responses = []
        for item in self.data:
            for response in item['responses']:
                responses.append({f"utter_{item['name'].replace(' ', '_').lower()}": [{"text": resp} for resp in response]})
        return responses

    def convert_slots(self):
        slots = self.data[0]['slots']  # Use the original slots data
        return slots

    def convert_stories(self):
        stories = []
        for item in self.data:
            story = {"story": item['name'].replace(' ', '_'), "steps": self.convert_steps(item)}
            stories.append(story)
        return stories

    def convert_steps(self, item):
        steps = []
        steps.append({"intent": item['name']})
        steps.append({"action": f"utter_{item['name'].replace(' ', '_').lower()}"})
        if 'actions' in item:
            for action in item['actions']:
                steps.append({"action": action})
        if 'active_loops' in item:
            for loop in item['active_loops']:
                steps.append({"active_loop": loop})
        if 'slot_was_set' in item:
            for slot in item['slot_was_set']:
                for key, value in slot.items():
                    steps.append({"slot_was_set": {key: value}})
        return steps


    def save_yaml(self, output_file, yaml_data):
        try:
            with open(output_file, 'w') as file:
                file.write(yaml_data)
        except IOError as e:
            logging.error(f"Error writing to YAML file: {e}")

def main():
    input_dir = 'rasa_training_files'
    output_dir = 'rasa_output_files'

    os.makedirs(output_dir, exist_ok=True)

    input_files = glob.glob(os.path.join(input_dir, '*.json'))

    for idx, input_file in enumerate(input_files):
        output_file = os.path.join(output_dir, f'converted_bigbot_data_{idx:03d}.yml')
        converter = JsonToYamlConverter(input_file)
        if converter.data:
            try:
                yaml_str = converter.convert_to_yaml()
                converter.save_yaml(output_file, yaml_str)
                logging.info(f"Successfully converted and saved {input_file} to {output_file}")
            except Exception as e:
                logging.error(f"Failed to convert {input_file} to YAML: {e}")

if __name__ == '__main__':
    main()
