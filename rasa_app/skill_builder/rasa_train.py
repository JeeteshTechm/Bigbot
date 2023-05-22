from flask import Flask, jsonify, request
from rasa_file_generator import RasaFileGenerator
from actions.run_actions import ActionServerManager
import json
import rasa

app = Flask(__name__)

@app.route('/file_generate', methods=['POST'])
def generate():
    try:
        uploaded_file = request.files['file']
        payload = json.load(uploaded_file)

        skill_id = str(payload["bot_id"])

        rasa_project = RasaFileGenerator(skill_id, payload)
        rasa_run_actions = ActionServerManager()

        rasa_project.create_rasa_folder_structure()
        rasa_project.generate_training_data()
        rasa_project.generate_domain_file()
        rasa_project.upload_config_file("input/config.yml")
        rasa_project.generate_actions_file()
        rasa_run_actions.start_action_server()

        return jsonify({"message": "Rasa files generated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/train', methods=['POST'])
def train():
    try:
        data = request.get_json()
        skill_id = data['skill_id']
        config = f"skills/{skill_id}/config.yml"
        training_files = f"skills/{skill_id}/data/"
        domain = f"skills/{skill_id}/domain.yml"
        output = f"skills/{skill_id}/models/"

        rasa.train(domain, config, [training_files], output, fixed_model_name='rasa_model')

        return jsonify({"message": "Rasa model has been trained and saved in models"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5005)

