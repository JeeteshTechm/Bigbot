import os
import json
import yaml
import requests
import shutil
from rasa_sdk import Action


class RasaFileGenerator:
    def __init__(self, skill_id, payload):
        self.skill_id = skill_id
        self.payload = payload

    def create_rasa_folder_structure(self):
        skill_path = f"./{self.skill_id}"
        action_path = f"{skill_path}/actions"
        data_path = f"{skill_path}/data"

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
            os.mkdir(data_path)
        except FileExistsError:
            print(f"Folder {data_path} already exists")
        else:
            print(f"Folder {data_path} created")

    def create_nlu_file(self):
        nlu_file = os.path.join(self.skill_id, "data", "nlu.yml")
        
        nlu_data = {"nlu": {}, "version": "3.1"}

        for intent in self.payload["intents"]:
            nlu_data["nlu"][intent["name"]] = {"examples": intent["utterances"]}

        yaml_data = yaml.dump(nlu_data)

        with open(nlu_file, "w") as yaml_file:
            yaml_file.write(yaml_data)

        return "success"


    def generate_domain_file(self):
        domain = {}
        domain['version'] = '3.4.4'

        intents = [{'name': intent['name']} for intent in self.payload['intents']]
        domain['intents'] = intents

        entities = [{'name': entity['name'], 'values': entity.get('values', [])} for entity in self.payload['entities']]
        domain['entities'] = entities

        session_config = {'session_expiration_time': 60, 'carry_over_slots_to_new_session': True}
        domain['session_config'] = session_config

        responses = {}
        for intent in self.payload['intents']:
            for response_idx, response_text in enumerate(intent['responses']):
                response_key = f'utter_{intent["name"]}_{response_idx}'
                responses[response_key] = [{'text': response_text}]
        domain['responses'] = responses

        actions = [{'name': f'action_{intent["name"]}', 'type': 'response'} for intent in self.payload['intents']]
        domain['actions'] = actions

        session_config = {'session_expiration_time': 60, 'carry_over_slots_to_new_session': True}
        domain['session_config'] = session_config

        domain_file_path = f"{self.skill_id}/domain.yml"

        with open(domain_file_path, "w") as f:
            yaml.dump(domain, f)

        return ('Domain saved to given path')

    def upload_config_file(self, config_file_path):
        shutil.copyfile(config_file_path, os.path.join(self.skill_id, 'config.yml'))
        return "Config file uploaded successfully"

    def generate_actions_file(self):
        actions_code = ""
        for intent in self.payload["intents"]:
            if "api_call" in intent:
                class_name = f"Action{intent['name'].title().replace(' ', '')}"
                actions_code += f"class {class_name}(Action):\n"
                actions_code += f"    def name(self) -> Text:\n"
                actions_code += f"        return 'action_{intent['name']}'\n\n"
                actions_code += f"    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:\n"
                actions_code += f"        return self._call_api_and_utter_response(dispatcher, tracker, domain)\n\n"
                actions_code += f"    def _call_api_and_utter_response(self, dispatcher, tracker, domain):\n"

                # check if API call requires request body
                if "request_body" in intent["api_call"]:
                    actions_code += f"        request_body = {json.dumps(intent['api_call']['request_body'], indent=2)}\n"
                else:
                    actions_code += f"        request_body = None\n"

                actions_code += f"        response = requests.{intent['api_call']['method']}('{intent['api_call']['url']}', json=request_body)\n"
                actions_code += f"        response_text = response.json()['{intent['response_field']}']\n"
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

    def create_stories_yml(self):
        # Create the data directory if it doesn't exist
        if not os.path.exists(f"{self.skill_id}/data"):
            os.makedirs(f"{self.skill_id}/data")
        
        # Create the stories.yml file
        with open(f"{self.skill_id}/data/stories.yml", 'w') as f:
            for intent in self.payload['intents']:
                f.write(f"- story: {intent['name']}\n")
                f.write("  steps:\n")
                for i, utterance in enumerate(intent['utterances']):
                    f.write(f"  - intent: {intent['name']}\n")
                    f.write(f"    - {utterance}\n")
                    f.write(f"    - action: utter_{intent['name']}_{i+1}\n")
                f.write("\n")
        return(f"Rules generated and saved in data/stories.yml")

    def generate_rules(self):
        rules = []
        for intent in self.payload['intents']:
            for utterance in intent['utterances']:
                rule = {
                    "rule": f"{intent['name']}_{utterance}",
                    "steps": [
                        {"intent": intent['name']},
                        {"text": utterance},
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

skill_id=str(payload["bot_id"])
rasa_file_generator = RasaFileGenerator(skill_id, payload)

rasa_file_generator.create_rasa_folder_structure()
rasa_file_generator.create_nlu_file()
rasa_file_generator.generate_domain_file()
rasa_file_generator.upload_config_file("config.yml")
rasa_file_generator.generate_actions_file()
rasa_file_generator.create_stories_yml()
rasa_file_generator.generate_rules()
