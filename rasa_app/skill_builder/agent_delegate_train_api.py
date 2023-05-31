from delegate_utterance_generator import IntentFilter
from flask import Flask, jsonify, request
from delegate_trainer import DelegateNluGenerator
from agent_utterance_generator import AgentDataCreator
from agent_train import AgentNluGenerator
import json
import rasa
import os

app = Flask(__name__)

def train_agent():
    with open("input/agent/agent.json", "r") as f:
        payload = json.load(f)
    skill_id="agent_bot"
    agent_train=AgentNluGenerator(skill_id,payload)
    agent_train.create_rasa_folder_structure()
    agent_train.nlu_yml()
    agent_train.upload_config_file("input/config.yml")
    agent_train.train_and_save_model()

def train_delegates(delegate_name,payload):
    skill_id= delegate_name
    delegate_train = DelegateNluGenerator(skill_id, payload)

    delegate_train.create_rasa_folder_structure()
    delegate_train.nlu_yml()
    delegate_train.upload_config_file("input/config.yml")
    delegate_train.train_and_save_model()


@app.route('/train_delegate', methods=['POST'])
def train_delegate():
    try:
        json_data = request.get_json()
        delegate_name = json_data['delegate_name']
        skill_ids=json_data["skill_ids"]

        intent_filter = IntentFilter()
        output_json = intent_filter.filter_intents(skill_ids, delegate_name)
        input_file= os.path.join("input","delegate", f"{delegate_name}.json")

        with open(input_file, "r") as f:
            payload = json.load(f)

        processor = AgentDataCreator(payload)
        processor.create_delegate_utterances(delegate_name)

        train_delegates(delegate_name,payload)

        train_agent()

        return jsonify({"message": "Rasa model has been trained and saved in models"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5009)

