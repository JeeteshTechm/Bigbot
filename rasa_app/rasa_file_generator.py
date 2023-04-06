import os
import json
import yaml
import requests
import shutil
from rasa_sdk import Action
from jsonschema import validate, ValidationError


class RasaFileGenerator:
    def __init__(self, skill_id, payload):
        self.skill_id = skill_id
        self.payload = payload

    def create_rasa_folder_structure(self):
        skill_path = f"./{self.skill_id}"
        action_path = f"{skill_path}/actions"
        data_path = f"{skill_path}/data"

        os.makedirs(skill_path, exist_ok=True)
        os.makedirs(action_path, exist_ok=True)
        os.makedirs(data_path, exist_ok=True)

    def create_nlu_file(self):
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

        with open(nlu_file, "w") as yaml_file:
            yaml_file.write(yaml_output)
        return "nlu created"

    def generate_domain_file(self):
        domain = {}
        domain['version'] = '3.4.4'

        intents = [{'name': intent['name']} for intent in payload['intents']]
        domain['intents'] = intents

        entity_list=[]
        for intent in payload["intents"]:
            if "entities" in intent:
                for entity in intent["entities"]:
                    entity_name = entity["name"]
                    entity_list.append(entity_name)

        entities = [{'name': entity} for entity in entity_list]
        domain['entities'] = entities

        responses = {}
        actions=[]
        for intent in payload['intents']:
            if 'api_call' in intent:
                actions.append(f'action_{intent["name"]}')
            else:
                for response_idx, response_text in enumerate(intent['responses']):
                    response_key = f'utter_{intent["name"]}'
                    responses[response_key] = [{'text': response_text}]

        domain['actions'] = actions
        
        domain['responses'] = responses
        domain["slots"]={}

        for intent in payload["intents"]:
            if "form" in intent:
                form_name = intent["form"]
                form_slots = intent["slots"]
                domain["forms"] = {form_name: {}}
                domain["forms"][form_name] = {"required_slots": [slot["name"] for slot in form_slots]}

                for slot in form_slots:
                    slot_name = slot["name"]
                    slot_type = slot["type"]
                    domain["slots"][slot_name] = { "type": slot_type,"mappings": [{"type": "from_entity", "entity": slot_name}]}
            


        session_config = {'session_expiration_time': 60, 'carry_over_slots_to_new_session': True}
        domain['session_config'] = session_config

        domain_file_path = f"{skill_id}/domain.yml"

        with open(domain_file_path, "w") as f:
            yaml.dump(domain, f, sort_keys=False)

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

    def generate_forms_code(self):
        # Load the Rasa validation schema from the JSON file
        with open(os.path.join(os.path.dirname(__file__), 'rasa_validation.json'), 'r') as f:
            rasa_validation_schema = json.load(f)

        forms_code = ""
        for form in self.payload.get('forms', []):
            # Validate the form configuration using the JSON schema
            try:
                validate(instance=form, schema=rasa_validation_schema["properties"]["domain"]["properties"]["forms"]["additionalProperties"])
                print(f"Validation successful for form {form['name']}")
            except ValidationError as e:
                print(f"Validation failed for form {form['name']}: {e.message}")
                continue

            class_name = f"{form['name'].title().replace(' ', '')}Form"
            forms_code += f"class {class_name}(FormValidationAction):\n"
            forms_code += f"    def name(self) -> Text:\n"
            forms_code += f"        return '{form['name']}'\n\n"

            for slot in form['slots']:
                if 'validation' in slot:
                    forms_code += f"    async def validate_{slot['name']}(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:\n"
                    forms_code += f"        return {{'{slot['name']}': slot_value}}\n\n"

        return forms_code

#     def create_stories_yml(self):
#         # Create the data directory if it doesn't exist
#         if not os.path.exists(f"{self.skill_id}/data"):
#             os.makedirs(f"{self.skill_id}/data")

#         # Create the stories.yml file
#         with open(f"{self.skill_id}/data/stories.yml", 'w') as f:
#             for intent in self.payload['intents']:
#                 f.write(f"- story: {intent['name']}\n")
#                 f.write("  steps:\n")
#                 f.write(f"  - intent: {intent['name']}\n")
#                 for i, response_text in enumerate(intent['responses']):
#                     f.write(f"    - action: utter_{intent['name']}_{i}\n")
#                 f.write("\n")
#         return(f"Stories generated and saved in data/stories.yml")

    def generate_stories_json(self):
            with open('payload3.json', 'r') as f:
                bot_data = json.load(f)
            intentList = []
            child=None
            for intent in bot_data['intents']:
                if(intent["parent_id"]==-1):
                    intentList.append(intent["name"])
                    child=intent["child_id"]
                for intent in bot_data["intents"]:
                    if(intent["id"]==child):
                        intentList.append(intent["name"])
                        child=intent["child_id"]
            return intentList
        
    def generate_stories(self,intents):
            story_dict = {
            "version": "3.1",
            "stories": [
                {
                    "story": f"Story path {'-'.join(intents)}"},
                {   "steps": []
                }
                    ]
            }
            for intent in intents:
                step_intent = {
                "intent": intent
                }
                step_action={"action":"utter_"+intent}
                story_dict["stories"][1]["steps"].append(step_intent)
                story_dict["stories"][1]["steps"].append(step_action)

            if not os.path.exists(f"{self.skill_id}/data"):
                os.makedirs(f"{self.skill_id}/data")
            with open(f"{self.skill_id}/data/stories.yml", "w") as f:
                yaml.dump(story_dict, f,default_flow_style=False,sort_keys=False)

#     def generate_rules(self):
#         rules = []
#         for intent in self.payload['intents']:
#             for utterance in intent['utterances']:
#                 rule = {
#                     "rule": f"{intent['name']}_{utterance}",
#                     "steps": [
#                         {"intent": intent['name']},
#                         {"text": utterance},
#                         {"action": f"utter_{intent['name']}"}
#                     ]
#                 }
#                 rules.append(rule)

#         data_dir = f"{self.skill_id}/data"
#         if not os.path.exists(data_dir):
#             os.makedirs(data_dir)

#         with open(f"{data_dir}/rules.yml", 'w') as f:
#             f.write("version: \"3.1\"\n\n")
#             for rule in rules:
#                 f.write("- rule: ")
#                 f.write(rule['rule'])
#                 f.write("\n  steps:\n")
#                 for step in rule['steps']:
#                     for key, value in step.items():
#                         f.write(f"    - {key}: {value}\n")

#         return(f"Rules generated and saved in {data_dir}/rules.yml")

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

                rule ={"rule": "Submit form", "condition": [{"active_loop": form_name}],
                        "steps": [
                                    {"action": form_name},
                                    {"active_loop": None},
                                    {"slot_was_set": [{"requested_slot": None}]},
                                    {"action": "utter_submit"},
                                    {"action": "utter_slots_values"}
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

        data_dir = f"{self.skill_id}/data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        with open(f"{data_dir}/rules.yml", 'w') as f:
            f.write("version: \"3.1\"\n\n")
            for rule in rules:
                f.write("- rule: ")
                f.write(rule['rule'])
                f.write("\n  steps:\n")
                for step in rule['steps']:
                    for key, value in step.items():
                        f.write(f"    - {key}: {value}\n")
                        
        return(f"Rules generated and saved in {data_dir}/rules.yml")


# read the JSON payload
with open("payload3.json", "r") as f:
    payload = json.load(f)

skill_id = str(payload["bot_id"])
rasa_file_generator = RasaFileGenerator(skill_id, payload)

rasa_file_generator.create_rasa_folder_structure()
rasa_file_generator.create_nlu_file()
rasa_file_generator.generate_domain_file()
rasa_file_generator.upload_config_file("config.yml")
rasa_file_generator.generate_actions_file()
intents=rasa_project.generate_stories_json()
rasa_project.generate_stories(intents)
# rasa_file_generator.create_stories_yml()
rasa_file_generator.generate_rules()



"""
This module automates the generation of necessary Rasa files based on a JSON payload from the Skill Builder. The main functionality of the module includes:

Creating the Rasa folder structure, including the main skill folder, actions folder, and data folder.
Generating the nlu.yml file, which contains the NLU training data.
Generating the domain.yml file, which describes the chatbot's domain (intents, entities, actions, etc.).
Uploading a pre-defined config.yml file.
Generating an actions.py file with custom action classes for API calls (if any).
Generating the stories.yml file, which contains example user-bot conversations (deprecated, replaced by rules.yml).
Generating the rules.yml file, which contains rules that determine the actions to be taken based on the user's intent.

In summary, this module reads the JSON payload, creates the necessary folder structure and generates the required files.
"""
