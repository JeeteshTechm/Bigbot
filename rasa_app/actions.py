from typing import Dict, Text, Any, List, Union

from rasa_sdk import Tracker, Action
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
import requests
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet
import json


def generate_form_class(form_config):
    form_name = form_config["form_name"]

    class GeneratedForm(Action):
        def name(self) -> Text:
            return form_name

        def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
            if "slots" in form_config:
                for slot_config in form_config["slots"]:
                    slot_name = slot_config["name"]
                    slot_utter = slot_config["utter"]
                    slot_value = tracker.get_slot(slot_name)

                    if not slot_value:
                        dispatcher.utter_message(response=slot_utter)
                        return [SlotSet(slot_name, None)]
            else:
                if form_name == "submit_restaurant_form":
                    cuisine = tracker.get_slot("cuisine")
                    num_people = tracker.get_slot("num_people")

                    slots = ['cuisine', 'num_people']

                    api_config = form_config["api"]
                    url = api_config["url"]
                    method = api_config["method"]
                    params = api_config["params"]

                    response = requests.request(method, url, params=params)
                    res = json.loads(response.text)
                    dispatcher.utter_message(res)

                    return [SlotSet("cuisine", None), SlotSet("num_people", None)]

            return []

    return GeneratedForm


with open("rasa_forms.json") as forms_file:
    forms_config = json.load(forms_file)

form_class_mapping = {}
for form_config in forms_config:
    form_name = form_config["form_name"]
    form_class = generate_form_class(form_config)
    form_class_mapping[form_name] = form_class


def get_form_class_by_name(form_name):
    return form_class_mapping.get(form_name, None)
