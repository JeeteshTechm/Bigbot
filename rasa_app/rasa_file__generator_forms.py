import os
import json
import yaml
import ast
import requests
import shutil
from rasa_sdk import Action
from ruamel.yaml import YAML
from collections import OrderedDict
import re
from typing import List

class RasaFileGenerator:
    def __init__(self, skill_id, payload):
        self.skill_id = skill_id
        self.payload = payload

    def create_rasa_folder_structure(self):
        skill_path = f"./{self.skill_id}"
        action_path = f"{skill_path}/actions"
        self.payload_path = f"{skill_path}/data"

        try:
            os.mkdir(skill_path)
        except FileExistsError:
            print(f"Folder {skill_path} already exists")
        else:
            print(f"Folder {skill_path} created")

        try:
            os.mkdir(action_path)
        except FileExistsError:
            print(f"Folder {action_path} already exists")
        else:
            print(f"Folder {action_path} created")

        try:
            os.mkdir(self.payload_path)
        except FileExistsError:
            print(f"Folder {self.payload_path} already exists")
        else:
            print(f"Folder {self.payload_path} created")

    def generate_rules(self):
        rules = []
        for intent in self.payload['intents']:
            if "form" in intent:
                form_name = intent["form"]
                trigger_intent = intent["name"]
                rule = {
                    "rule": f"Activate form",
                    "steps": [
                        {"intent": trigger_intent},
                        {"action": form_name},
                        {"active_loop": form_name}
                    ]
                }
                rules.append(rule)
            else:
                rule = {
                    "rule": f"{intent['name']}",
                    "steps": [
                        {"intent": intent['name']},
                        {"action": f"utter_{intent['name']}"}
                    ]
                }
                submit={
                     "rule": f"submit form",
                    "condition": f"\n    - active_loop: {form_name}",
                    "steps": [
                        {"action": form_name},
                        {"active_loop":"null"},
                        {"action": "utter_submit"},
                        {"action": "utter_slots_values"}
                    ]

                }
                rules.append(rule)
                rules.append(submit)

        return rules

    def create_combined_yml(self, rules):
        nlu_file = os.path.join(self.skill_id, "data", "nlu.yml")
        intents = self.payload["intents"]
        yaml_output = "version: '3.1'\n"
        yaml_output += "nlu:\n"
        for intent in intents:
            if "entities" in intent:
                yaml_output += f"  - intent: {intent['name']}\n"
                yaml_output += "    examples: |\n"
                for example in intent['utterances']:
                    example_with_entities = example
                    for entity in intent['entities']:
                        for value in entity['values']:
                            if str(value) in example_with_entities:
                                example_with_entities = example_with_entities.replace(str(value), f"[{value}]({entity['name']})")
                    yaml_output += f"      - {example_with_entities}\n"

            else:
                yaml_output += f"  - intent: {intent['name']}\n"
                yaml_output += "    examples: |\n"
                for example in intent['utterances']:
                    yaml_output += f"      - {example}\n"

        yaml_output += "rules:\n"
        for rule in rules:
            yaml_output += f"  - rule: {rule['rule']}\n"
            if "submit" in rule['rule']:
                yaml_output+=f"    condition: {rule['condition']}\n"
            yaml_output += "    steps:\n"
            for step in rule['steps']:
                for key, value in step.items():
                    yaml_output += f"      - {key}: {value}\n"

        with open(nlu_file, "w") as yaml_file:
            yaml_file.write(yaml_output)

        return f"Combined YAML file generated and saved in {nlu_file}"

    def generate_training_data(self):
        rules = self.generate_rules()
        result = self.create_combined_yml(rules)
        return result

    def generate_domain_file(self):
        intents = self.payload["intents"]
        yaml_output = "version: '3.1'\n"
        yaml_output += "intents:\n"
        for intent in intents:
            if "form" in intent:
                yaml_output += f"  - {intent['name']}:\n"
                yaml_output += "    use_entities: []\n"
            else:
                yaml_output += f"  - {intent['name']}\n"

        for intent in intents:
            if "form" in intent:
                yaml_output += f"slots:\n"
                for slot in intent['slots']:
                    yaml_output += f"  {slot['name']}:\n"
                    yaml_output += f"    type: {slot['type']}\n"
                    yaml_output += f"    influence_conversation: false\n"
                    yaml_output += f"    mappings:\n"
                    yaml_output += f"    - type : from_entity\n"
                    yaml_output += f"      entity : {slot['name']}\n"

        for intent in intents:
            if "form" in intent:
                yaml_output += f"forms:\n"
                yaml_output += f"  {intent['form']}:\n"
                yaml_output += f"    required_slots:\n"
                for slot in intent['slots']:
                    yaml_output += f"      - {slot['name']}\n"

        yaml_output += "entities:\n"
        for intent in intents:
            if "form" in intent:
                for slot in intent['slots']:
                    yaml_output += f"  - {slot['name']}\n"

        session_config = {'session_expiration_time': 60, 'carry_over_slots_to_new_session': True}
        yaml_output += "session_config:\n"
        for key, value in session_config.items():
            yaml_output += f"  {key}: {value}\n"

        domain_file_path = f"{self.skill_id}/domain.yml"

        responses = {}
        actions = []
        for intent in intents:
            if "form" in intent:
                actions.append(f'validate_{intent["form"]}_form')
                
                responses['utter_submit'] = [{'text': "All done!"}]
                slot_values_template = "I am going to use the following parameters:\n"
                for slot in intent['slots']:
                    if "bot_ask_positive" in slot:
                        responses[f"utter_ask_{slot['name']}"] = [{'text': slot["bot_ask_positive"]}]
                    if "bot_ask_negative" in slot:
                        responses[f"utter_wrong_{slot['name']}"] = [{'text': slot["bot_ask_negative"]}]


                    slot_values_template += f"            - {slot['name']}: {{{slot['name']}}}\n"
                responses['utter_slots_values'] = [{'text': slot_values_template}]
            else:
                response_key = f'utter_{intent["name"]}'
                response_texts = intent['responses']
                responses[response_key] = [{'text': response_text} for response_text in response_texts]

        yaml_output += "responses:\n"
        for response_key, response_texts in responses.items():
            yaml_output += f"  {response_key}:\n"
            for response_text in response_texts:
                yaml_output += f"    - text: {response_text['text']}\n"

        yaml_output += "actions:\n"
        for action in actions:
            yaml_output += f"  - {action}\n"

        with open(domain_file_path, "w") as f:
            f.write(yaml_output)

        return ('Domain saved to given path')


    def upload_config_file(self, config_file_path):
        shutil.copyfile(config_file_path, os.path.join(self.skill_id, 'config.yml'))
        return "Config file uploaded successfully"
   

    def generate_actions_file(self):
        actions_template = """from typing import Dict, Text, Any, List, Union

from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction


class Validate{form}Form(FormValidationAction):

    def name(self) -> Text:
        return "validate_{form}_form"

    {validations}
    """

        form_validations = {}

        for intent in self.payload["intents"]:
            if "form" in intent:
                form_name = intent["form"]
                if form_name not in form_validations:
                    form_validations[form_name] = []
                if "slots" in intent:
                    for slot in intent["slots"]:
                        slot_name = slot["name"]
                        form_validations[form_name].append(slot_name)

        actions = ""
        for form_name, slots in form_validations.items():
            validations = ""
            for slot in slots:
                validations += f"""
    def validate_{slot}(self, value: Text, dispatcher: CollectingDispatcher,
                            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        \"\"\"Validate {slot} value.\"\"\"

        if value:
            return {{ "{slot}": value }}
        else:
            dispatcher.utter_message(response="utter_ask_{slot}")
            # validation failed, set this slot to None, meaning the
            # user will be asked for the slot again
            return {{ "{slot}": None }}
            \n"""

            actions += actions_template.format(form=form_name, validations=validations)

        # create the actions folder if it doesn't exist
        actions_folder_path = os.path.join(self.skill_id, "actions")
        os.makedirs(actions_folder_path, exist_ok=True)

        # write the actions code to a file
        actions_file_path = os.path.join(actions_folder_path, "actions.py")
        with open(actions_file_path, "w") as f:
            f.write(actions)

        # create an empty __init__.py file
        init_file_path = os.path.join(actions_folder_path, "__init__.py")
        with open(init_file_path, "w") as f:
            pass

        return f"Actions saved to {actions_file_path}"

# read the JSON payload
with open("paylod.json", "r") as f:
    payload = json.load(f)

skill_id=str(payload["bot_id"])
rasa_project = RasaFileGenerator(skill_id, payload)

rasa_project.create_rasa_folder_structure()
rasa_project.generate_training_data()
rasa_project.generate_domain_file()
rasa_project.upload_config_file("config.yml")
rasa_project.generate_actions_file()
