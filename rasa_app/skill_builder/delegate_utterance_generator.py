import json
import os

class IntentFilter:
    def __init__(self):
        self.input_file = "input/skills.json"

    def filter_intents(self, intents, delegate_name):
        with open(self.input_file, "r") as file:
            input_json = json.load(file)

        output_json = {"intents": []}

        for intent in input_json["intents"]:
            if intent["name"] in intents:
                output_json["intents"].append(intent)

        # Save output JSON using the delegate name
        output_file = os.path.join("input","delegate", f"{delegate_name}.json")
        with open(output_file, "w") as file:
            json.dump(output_json, file, indent=4)

        return output_json



"""intent_filter = IntentFilter(input_file)
intents_to_filter = ["restaurant", "f52a6e41-e7cd-44ea-aeef-b5bda1de0f9d"]
delegate_name = "delegate1"
output_json = intent_filter.filter_intents(intents_to_filter, delegate_n"""ame)
