import yaml
import json

def generate_stories_json():
    with open('payload4.json', 'r') as f:
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



def generate_stories(intents):
    story_dict = {
    "version": "3.0",
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

    with open("tories.yml", "w") as f:
        yaml.dump(story_dict, f)

intents=generate_stories_json()
generate_stories(intents)







