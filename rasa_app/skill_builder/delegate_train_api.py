

from delegate_utterance_generator import IntentFilter
from flask import Flask, jsonify, request
from delegate_train import NluGenerator
import json
import rasa

app = Flask(__name__)

@app.route('/train_delegate', methods=['POST'])
def train_delegate():
    try:
        json_data = request.get_json()
        delegate_name = json_data['delegate_name']
        skill_ids=json_data["skill_ids"]

        intent_filter = IntentFilter(input_file)
        output_json = intent_filter.filter_intents(intents_to_filter, delegate_name)
        input_file= os.path.join("input","delegate", f"{delegate_name}.json")

        with open(input_file, "r") as f:
            payload = json.load(f)

        skill_id= delegate_name
        rasa_project = NluGenerator(skill_id, payload)

        rasa_project.create_rasa_folder_structure()
        rasa_project.nlu_yml()
        rasa_project.upload_config_file("input/config.yml")
        rasa_project.train_and_save_model()


        return jsonify({"message": "Rasa model has been trained and saved in models"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5009)

