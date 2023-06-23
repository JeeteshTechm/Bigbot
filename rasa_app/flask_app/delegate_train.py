from delegate_utterance_generator import IntentFilter
from flask import Flask, jsonify, request
from delegate_trainer import DelegateNluGenerator
from agent_utterance_generator import AgentDataCreator
from agent_train import AgentNluGenerator
from flask_cors import CORS, cross_origin
import json
import rasa
import os

app = Flask(__name__)


def train_delegates(delegate_name,payload):
    skill_id= delegate_name
    delegate_train = DelegateNluGenerator(skill_id, payload)

    delegate_train.create_rasa_folder_structure()
    delegate_train.nlu_yml()
    delegate_train.upload_config_file("input/config.yml")
    delegate_train.train_and_save_model()


@app.route('/train_delegate', methods=['POST'])
@cross_origin()
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

        train_delegates(delegate_name,payload)

        return jsonify({"message": "Delegate models are trained"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5009)

