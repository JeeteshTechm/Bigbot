import yaml
import json

class RuleConverter:
    def __init__(self):
        self.json_objects = []

    def convert_rules_to_json(self, yaml_content):
        data = yaml.safe_load(yaml_content)

        if 'rules' in data:
            rules = data['rules']
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

                    self.json_objects.append(rule_json)

        json_str = json.dumps(self.json_objects, indent=2)
        with open('converted_rules.json', 'w') as file:
            file.write(json_str)

        return json_str


with open('stories.yml', 'r') as file:
    yaml_content = file.read()

rule_converter = RuleConverter()

json_str = rule_converter.convert_rules_to_json(yaml_content)

