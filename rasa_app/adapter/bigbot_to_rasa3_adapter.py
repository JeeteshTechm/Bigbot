import json
import yaml
import os

class JSONToYAMLConverter:
    def __init__(self, json_payload):
        self.payload = json_payload

    def generate_stories(self):
        stories = []
        for intent in self.payload['intents']:
            if "form" in intent:
                form_name = intent["form"]
                trigger_intent = intent["intent"]
                rule = {
                    "story": intent["story_name"],
                    "steps": [
                        {"intent": trigger_intent},
                        {"action": form_name},
                        {"active_loop": form_name},
                        {"active_loop": None},
                    ]
                }
                stories.append(rule)

                if "slots" in intent:
                    form_name = intent["form"]
                    trigger_intent = intent["intent"]
                    rule = {
                        "story": intent["story_name"],
                        "steps": [
                            {"intent": trigger_intent},
                            {"action": form_name},
                            {"active_loop": form_name},
                        ]
                    }

                    for slot in intent["slots"]:
                        slot_name = slot["name"]
                        examples = slot["examples"]
                        for example in examples:
                            slot_was_set = {"slot_was_set": [{slot_name: example}]}
                            rule["steps"].extend([
                                {"active_loop": form_name},
                                slot_was_set,
                                {"action": form_name}
                            ])

                    rule["steps"].extend([
                        {"action": form_name + "_action"}
                    ])

                    stories.append(rule)       
            else:
                rule = {
                    "story": intent["story_name"],
                    "steps": [
                        {"intent": intent['intent']},
                        {"action": f"utter_{intent['intent']}"}
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
        actions = set() 

        for intent in intents:
            yaml_output += f"  - intent: {intent['intent']}\n"
            yaml_output += "    examples: |\n"
            for example in intent['utterances']:
                yaml_output += f"      - {example}\n"

            response_key = intent['response_name']
            response_texts = intent['response']
            responses[response_key] = [{'text': response_text} for response_text in response_texts]

            if "slots" in intent:
                for slot in intent["slots"]:
                    slot_name = slot["name"]
                    slot_bot_ask = slot["bot_ask"]
                    slot_response_key = f'utter_ask_{slot_name}'
                    responses[slot_response_key] = [{'text': slot_bot_ask}]
                    slot_type = slot["type"]
                    slots[slot_name] = {
                        "type": "text",
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
                        if slot_name not in form_slots:
                            form_slots[slot_name] = []
                        form_slots[slot_name].append({"type": "from_text"})
           
            for action in intent.get("actions", []):
                if not (action.startswith("utter_") or action.endswith("form")):
                    actions.add(action)
        
        # Output actions
        yaml_output += "actions:\n"
        for action in actions:
            yaml_output += f"  - {action}\n"
        

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
#print(yaml_data)
