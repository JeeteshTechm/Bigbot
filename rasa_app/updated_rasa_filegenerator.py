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
                rules.append(rule)

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
                            example_with_entities = example_with_entities.replace(value, f"[{value}]({entity['name']})")
                    yaml_output += f"      - {example_with_entities}\n"
            else:
                yaml_output += f"  - intent: {intent['name']}\n"
                yaml_output += "    examples: |\n"
                for example in intent['utterances']:
                    yaml_output += f"      - {example}\n"

        yaml_output += "rules:\n"
        for rule in rules:
            yaml_output += f"  - rule: {rule['rule']}\n"
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
            yaml_output += f"  - {intent['name']}\n"

        session_config = {'session_expiration_time': 60, 'carry_over_slots_to_new_session': True}
        yaml_output += "session_config:\n"
        for key, value in session_config.items():
            yaml_output += f"  {key}: {value}\n"

        domain_file_path = f"{self.skill_id}/domain.yml"

        responses = {}
        actions = []
        for intent in intents:
            if "api_call" in intent:
                actions.append(f'action_{intent["name"]}')
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

        forms = {}
        slots = set()
        for intent in intents:
            if "form" in intent:
                form_name = intent["form"]
                form_slots = intent["slots"]
                forms[form_name] = {"required_slots": [slot["name"] for slot in form_slots]}
                for slot in form_slots:
                    slot_name = slot["name"]
                    slot_type = slot["type"]
                    slots.add(slot_name)
                    forms[form_name][slot_name] = {"type": slot_type, "mapping": [{"type": "from_entity", "entity": slot_name}]}

        yaml_output += "forms:\n"
        for form_name, form_data in forms.items():
            yaml_output += f"  {form_name}:\n"
            yaml_output += f"    required_slots: {form_data['required_slots']}\n"
            for slot_name, slot_data in form_data.items():
                if slot_name != "required_slots":
                    yaml_output += f"    {slot_name}:\n"
                    yaml_output += f"      type: {slot_data['type']}\n"
                    yaml_output += f"      mappings:\n"
                    for mapping in slot_data["mapping"]:
                        yaml_output += f"        - type: {mapping['type']}\n"
                        yaml_output += f"          entity: {mapping['entity']}\n"

        yaml_output += "slots:\n"
        for slot in slots:
            yaml_output += f"  {slot}:\n"
            yaml_output += f"    type: unfeaturized\n"

        with open(domain_file_path, "w") as f:
            f.write(yaml_output)

        return ('Domain saved to given path')



    def upload_config_file(self, config_file_path):
        shutil.copyfile(config_file_path, os.path.join(self.skill_id, 'config.yml'))
        return "Config file uploaded successfully"

    def generate_actions_file(self):
        actions_code = ""
        for intent in self.payload["intents"]:
            if "form" in intent:
                actions_code +=  f"from typing import Any, Text, Dict, List, Union\n"
                actions_code +=  f"from rasa_sdk import Action, Tracker\n"
                actions_code +=  f"from rasa_sdk.executor import CollectingDispatcher\n"
                actions_code +=  f"import request\n"
                actions_code +=  f" \n"
                class_name = f"Action{intent['name'].title().replace(' ', '')}"
                class_name=class_name.replace("_","")
                actions_code += f"class {class_name}(FormAction):\n"
                actions_code += f"    def name(self) -> Text:\n"
                actions_code += f"        return '{intent['form']}'\n\n"
                actions_code += f"    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:\n"
                
                actions_code += f"        return self._call_api_and_utter_response(dispatcher, tracker, domain)\n\n"
                actions_code += f"    def _call_api_and_utter_response(self, dispatcher, tracker, domain):\n"

                required_slots=[]
                if "slots" in intent:
                    for slots in intent["slots"]:
                        slot_name = slots["name"]
                        required_slots.append(slot_name)
            
                for i in required_slots:  
                    actions_code += f"        {i} = tracker.get_slot({i})\n"
    
                required_slots = ["cuisine", "num_people"]
                actions_code += f"        response = requests.{intent['api_call']['method']}('{intent['api_call']['url']}', json=request_body)\n"
                actions_code += f"        response_text = response.json()\n"
                actions_code += f"        dispatcher.utter_message(text=response_text)\n\n"

            if "api_call" in intent and not "form" in intent:
                class_name = f"Action{intent['name'].title().replace(' ', '')}"
                class_name=class_name.replace("_","")
                actions_code += f"class {class_name}(Action):\n"
                
                actions_code += f"    def name(self) -> Text:\n"
                actions_code += f"        return 'action_{intent['name']}'\n\n"

                actions_code += f"    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:\n"
                actions_code += f"        return self._call_api_and_utter_response(dispatcher, tracker, domain)\n\n"
                actions_code += f"    def _call_api_and_utter_response(self, dispatcher, tracker, domain):\n"

                # check if API call requires request body
                entity_list=[]
                if "entities" in intent:
                    for entity in intent["entities"]:
                        entity_name = entity["name"]
                        entity_list.append(entity_name)
                #entity_list = [ast.literal_eval(s) for s in entity_list]


                request_body_list=intent["api_call"]["request_body"]

                request_body = dict(zip(request_body_list, entity_list))
                
                
                for key, value in request_body.items():
                    
                    actions_code += f"        {value} = tracker.get_slot({value})\n"
               

                actions_code += f"        response = requests.{intent['api_call']['method']}('{intent['api_call']['url']}', json=request_body)\n"
                actions_code += f"        response_text = response.json()\n"
                actions_code += f"        dispatcher.utter_message(text=response_text)\n\n"

        # create the actions folder if it doesn't exist
        actions_folder_path = os.path.join(self.skill_id, "actions")
        os.makedirs(actions_folder_path, exist_ok=True)

        # write the actions code to a file
        actions_file_path = os.path.join(actions_folder_path, "actions.py")
        with open(actions_file_path, "w") as f:
            f.write(actions_code)

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
