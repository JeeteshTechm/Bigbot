import logging
from flask import Flask, jsonify, request
from rasa_file_generator import RasaFileGenerator
from actions.run_actions import ActionServerManager
import json
import rasa
import logging
app = Flask(__name__)

logging.basicConfig(level=logging.INFO, filename='logs/skill_builder_train.log')
logging.basicConfig(level=logging.INFO)

def rasa_file_generator(payload):
    skill_id = str(payload["bot_id"])
    logging.info(f"Generating Rasa files for skill ID: {skill_id}")

    rasa_project = RasaFileGenerator(skill_id, payload)
    rasa_run_actions = ActionServerManager()

    rasa_project.create_rasa_folder_structure()
    rasa_project.generate_training_data()
    rasa_project.generate_domain_file()
    rasa_project.upload_config_file("input/config.yml")
    rasa_project.generate_actions_file()
    rasa_run_actions.start_action_server()

    logging.info("Rasa files generation completed")

def rasa_train(skill_id):
    logging.info(f"Training Rasa model for skill ID: {skill_id}")

    config = f"skills/{skill_id}/config.yml"
    training_files = f"skills/{skill_id}/data/"
    domain = f"skills/{skill_id}/domain.yml"
    output = f"skills/{skill_id}/models/"

    rasa.train(domain, config, [training_files], output, fixed_model_name='rasa_model')

    logging.info("Rasa model training completed")

@app.route('/skill_builder_train', methods=['POST'])
def generate():
    try:
        payload = request.get_json()
        skill_id = str(payload["bot_id"])
        rasa_file_generator(payload)
        rasa_train(skill_id)

        return jsonify({"message": "Rasa model has been trained and saved in models"})
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5006)

