import yaml
import json


class YamlToJsonConverter:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = None

    def load_yaml(self):
        with open(self.file_path, 'r') as file:
            self.data = yaml.safe_load(file)

    def process_steps(self, steps):
        intent = ''
        responses = []
        form_slots = []
        actions = []
        utterances = []

        for step in steps:
            if 'intent' in step:
                intent = step['intent']
                if 'utterances' in step:
                    utterances = step['utterances']
            if 'action' in step:
                action = step['action']

                if action.startswith('utter'):
                    response = action.split('_')[-1]
                    responses.append(response)
                elif action.startswith('action_ask'):
                    slot_name = action.split('_')[-1]
                    slot = {
                        "name": slot_name,
                        "type": "text"
                    }
                    form_slots.append(slot)
                else:
                    actions.append(action)

        actions = [x for x in actions if x]

        processed_json = {
            "name": intent,
            "utterances": utterances,
            "responses": responses,
            "actions": actions
        }

        if form_slots:
            processed_json["form"] = {
                "name": intent + "_form",
                "slots": form_slots
            }

        return processed_json

    def convert_to_json(self):
        json_objects = {}

        for key in ['rules', 'stories']:
            if key in self.data:
                for item in self.data[key]:
                    steps = item['steps']
                    if steps:
                        processed_json = self.process_steps(steps)
                        json_objects[processed_json['name']] = processed_json

        unique_json_objects = list(json_objects.values())

        json_str = json.dumps(unique_json_objects, indent=2)

        with open('converted_bigbot_data.json', 'w') as file:
            file.write(json_str)

        return json_str


def main():
    converter = YamlToJsonConverter('rasa_input.yml')
    converter.load_yaml()
    json_str = converter.convert_to_json()


if __name__ == "__main__":
    main()
