import logging
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from skill_file_generator import RasaFileGenerator
from skill_utterance_generator import JSONDataProcessor
from actions.run_actions import ActionServerManager
from agent_train import AgentNluGenerator
import json
import rasa

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO, filename='logs/skill_builder_train.log')

def rasa_file_generator(payload):
    skill_id = str(payload["bot_id"])
    logging.info(f"Generating Rasa files for skill ID: {skill_id}")

    has_form = any("form" in intent for intent in payload["intents"])

    processor = JSONDataProcessor(payload)
    processor.create_delegate_utterances()

    rasa_project = RasaFileGenerator(skill_id, payload)
    rasa_run_actions = ActionServerManager()

    rasa_project.create_rasa_folder_structure()
    rasa_project.generate_training_data()
    rasa_project.generate_domain_file()
    rasa_project.upload_config_file("input/config.yml")

    if has_form:
        print("Yes, at least one intent has a form.")
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

def train_agent():
    with open("input/skills.json", "r") as f:
        payload = json.load(f)
    skill_id="agent_bot"
    agent_train=AgentNluGenerator(skill_id,payload)
    agent_train.create_rasa_folder_structure()
    agent_train.nlu_yml()
    agent_train.upload_config_file("input/config.yml")
    agent_train.train_and_save_model()


@app.route('/skill_builder_train', methods=['POST'])
@cross_origin()
def generate():
    try:
        payload = request.get_json()
        payload["intents"]=[intent for intent in payload["intents"] if intent]
        skill_id = str(payload["bot_id"])
        rasa_file_generator(payload)
        rasa_train(skill_id)
        train_agent()

        return jsonify({"message": "Rasa model has been trained and saved in models"})
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500


    

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5002)
