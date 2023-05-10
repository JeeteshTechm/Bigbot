import yaml
import json

class YamlToJsonConverter:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = None

    def load_yaml(self):
        with open(self.file_path, 'r') as file:
            self.data = yaml.safe_load(file)

    def convert_to_json(self):
        json_objects = {}

        if 'rules' in self.data:
            rules = self.data['rules']
            for rule in rules:
                steps = rule['steps']
                if steps:
                    intent = steps[0]['intent']
                    responses = []
                    form_slots = []
                    actions = []
                    for step in steps[1:]:
                        action = step.get('action', '')
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

                    rule_json = {
                        "intents": [
                            {
                                "name": intent,
                                "responses": responses,
                                "actions": actions
                            }
                        ]
                    }

                    if form_slots:
                        rule_json["forms"] = [
                            {
                                "name": intent + "_form",
                                "slots": form_slots
                            }
                        ]

                    json_objects[intent] = rule_json

        if 'stories' in self.data:
            stories = self.data['stories']
            for story in stories:
                steps = story['steps']
                if steps:
                    intent = ''
                    responses = []
                    actions = []
                    form_slots = []

                    for step in steps:
                        if 'intent' in step:
                            intent = step['intent']
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

                    story_json = {
                        "intents": [
                            {
                                "name": intent,
                                "responses": responses,
                                "actions": actions
                            }
                        ]
                    }

                    if form_slots:
                        story_json["forms"] = [
                            {
                                "name": intent + "_form",
                                "slots": form_slots
                            }
                        ]

                    json_objects[intent] = story_json

        unique_json_objects = list(json_objects.values())

        json_str = json.dumps(unique_json_objects, indent=2)

        
        with open('converted_data.json', 'w') as file:
            file.write(json_str)

        return json_str


converter = YamlToJsonConverter('rules_stories.yml')

converter.load_yaml()

json_str = converter.convert_to_json()
