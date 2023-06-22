import json
import yaml
import os

class JSONToYAMLConverter:
    def __init__(self, json_payload):
        self.payload = json_payload

    def generate_stories(self):
        stories = []
        blocks = {block['id']: block for block in self.payload['blocks']}
        for block in self.payload['blocks']:
            for intent in block['intents']:
                if "form" in block:
                    form_name = block["form"]["name"]
                    rule = {
                        "story": f"{intent['name']}_activateform",
                        "steps": [
                            {"intent": intent['name']},
                            {"action": form_name},
                            {"active_loop": form_name},
                            {"active_loop": None},
                        ]
                    }

                    if "slots" in block:
                        slot_was_set = []
                        for slot in block["slots"]:
                            slot_name = slot["name"]
                            slot_was_set.append({slot_name: None})  # assuming empty slot value
                            rule["steps"].append({"slot_was_set": slot_was_set})

                    stories.append(rule)

                else:
                    rule = {
                        "story": f"{block['id']}_story",
                        "steps": [
                            {"intent": intent['name']},
                            {"action": f"utter_{intent['responses'][0]['name']}"},
                        ]
                    }
                    stories.append(rule)
        return stories


    def convert_to_yaml(self):
        stories = self.generate_stories()
        intents = self.payload["intents"]
        yaml_output = "version: '3.1'\n"
        yaml_output += "nlu:\n"
        responses = {}
        slots = {}
        forms = {}

        for intent in intents:
            yaml_output += f"  - intent: {intent['name']}\n"
            yaml_output += "    examples: |\n"
            for example in intent['utterances']:
                yaml_output += f"      - {example}\n"

            response_key = f'utter_{intent["name"]}'
            response_texts = intent['responses']
            responses[response_key] = [{'text': response_text} for response_text in response_texts]

            if "slots" in intent:
                for slot in intent["slots"]:
                    slot_name = slot["name"]
                    slot_bot_ask = slot["bot_ask"]
                    slot_response_key = f'utter_ask_{slot_name}'
                    responses[slot_response_key] = [{'text': slot_bot_ask}]
                    slot_type = slot["type"]
                    slots[slot_name] = {
                        "type": slot_type,
                        "influence_conversation": True
                    }

            if "form" in intent:
                form_name = intent["form"]
                if form_name not in forms:
                    forms[form_name] = {}

                if "slots" in intent:
                    form_slots = forms[form_name]
                    for slot in intent["slots"]:
                        slot_name = slot["name"]
                        slot_type = slot["type"]
                        if slot_name not in form_slots:
                            form_slots[slot_name] = []
                        form_slots[slot_name].append({"type": slot_type})

        yaml_output += "responses:\n"
        for response_key, response_texts in responses.items():
            yaml_output += f"  {response_key}:\n"
            for response_text in response_texts:
                yaml_output += f"    - text: {response_text['text']}\n"

        yaml_output += "slots:\n"
        for slot_name, slot_data in slots.items():
            yaml_output += f"  {slot_name}:\n"
            yaml_output += f"    type: {slot_data['type']}\n"
            yaml_output += "    influence_conversation: true\n"

        yaml_output += "forms:\n"
        for form_name, form_slots in forms.items():
            yaml_output += f"  {form_name}:\n"
            for slot_name , slot_list in form_slots.items():
                yaml_output += f" {slot_name}:\n"
                for slot_data in slot_list:
                    yaml_output += f" - type: {slot_data['type']}\n"

        yaml_output += "stories:\n"
        for story in stories:
            yaml_output += f"  - story: {story['story']}\n"
            yaml_output += "    steps:\n"
            for step in story['steps']:
                for key, value in step.items():
                    yaml_output += f"      - {key}: {value}\n"

        return yaml_output
#json_converter = JSONToYAMLConverter("input/sindalah.json")
#yml_data = json_converter.convert_to_yaml()
