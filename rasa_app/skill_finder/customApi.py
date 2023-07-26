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
from remove_empty_keys_yaml import YamlFileProcessor

class RasaFileGenerator:
    def __init__(self, payload):
        self.payload = payload
        self.output_file = 'input/skills.json'

    def generate_actions_file(self):
        actions_template = """
from typing import Dict, Text, Any, List, Union
from rasa_sdk import Tracker,Action
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
import requests
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet 
import json
class Validate{form}Form(Action):
    def name(self) -> Text:
        return "validate_{form}_form"

    {validations}

class Submit{form}Form(Action):
    def name(self) -> Text:
        return "submit_{form}_form"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
        {slot_assignments}

        {api_assignments}

        return [{reset_slot_assignments}]
"""

        form_validations = {}
        slot_names = []

        for intent in self.payload["intents"]:
            if "form" in intent:
                form_name = intent["form"]
                if form_name not in form_validations:
                    form_validations[form_name] = []
                if "slots" in intent:
                    for slot in intent["slots"]:
                        slot_name = slot["name"]
                        slot_names.append(slot_name)
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
"""

            slot_assignments = ""
            form_slot_assignments = ""
            form_reset_slot_assignments = ""
            api_assignments = ""
            reset_slot_assignments = ""
            api_payload=""
            for slot in slots:
                form_reset_slot_assignments += f"SlotSet(\"{slot}\", None),"

            for i, slot in enumerate(slots):
                if i == 0:
                    form_slot_assignments += f"{slot} = tracker.get_slot('{slot}')\n"
                    api_payload =api_payload+f"{slot}"
                    print(api_payload)
                else:
                    form_slot_assignments += "        " + f"{slot} = tracker.get_slot('{slot}')\n"
                    api_payload =f"{slot}"

            for intent in self.payload["intents"]:
                if "form" in intent and "api_call" in intent and intent["form"] == form_name:
                    api_method = intent["api_call"].get("method")
                    api_url = intent["api_call"].get("url")\
                    
                    api_assignments += f"response = requests.request('{api_method}', '{api_url}', json={api_payload})\n"
                    break  # Break the loop after finding the matching intent

            reset_slot_assignments += f"\n        # Slot reset for {form_name}\n        {form_reset_slot_assignments}"
            slot_assignments += form_slot_assignments

            actions += actions_template.format(
                form=form_name,
                validations=validations,
                slot_assignments=slot_assignments,
                api_assignments=api_assignments,
                reset_slot_assignments=reset_slot_assignments
            )

        with open("actions/actions4.py", "w") as f:
            f.write(actions)

        return "Actions saved"


with open("input/hotel.json", "r") as f:
    payload = json.load(f)

rasa_project = RasaFileGenerator(payload)
rasa_project.generate_actions_file()

