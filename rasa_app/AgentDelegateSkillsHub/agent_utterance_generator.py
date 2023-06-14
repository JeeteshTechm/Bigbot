import json
import os

class AgentDataCreator:
    def __init__(self, payload):
        self.payload = payload
        self.output_file ='input/agent/agent.json'

    def create_delegate_utterances(self, delegate_name):
        if os.path.exists(self.output_file) and os.stat(self.output_file).st_size > 0:
            with open(self.output_file, 'r') as file:
                main_data = json.load(file)
        else:
            main_data = {"intents": []}

        output_data = {
            "name": delegate_name,
            "utterances": []
        }

        # Check if intent with the same name already exists
        existing_intent_index = None
        for i, intent in enumerate(main_data["intents"]):
            if intent["name"] == delegate_name:
                existing_intent_index = i
                break

        # Append utterances to the output_data
        for intent in self.payload["intents"]:
            if "utterances" in intent:
                output_data["utterances"].extend(intent["utterances"])

        # If existing intent found, replace it
        if existing_intent_index is not None:
            main_data["intents"][existing_intent_index] = output_data
        else:
            main_data["intents"].append(output_data)

        with open(self.output_file, 'w') as file:
            json.dump(main_data, file, indent=4)

        print(f"Data appended to {self.output_file}.")



"""with open("input/delegate/delegate8.json", 'r') as file:
    payload = json.load(file)
processor = AgentDataCreator(payload)
processor.create_delegate_utterances("delegate8")"""
