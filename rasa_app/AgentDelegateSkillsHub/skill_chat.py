import logging
import os
from flask import Flask, jsonify, request
from rasa.core.agent import Agent
from rasa.utils.endpoints import EndpointConfig
from rasa.core.tracker_store import SQLTrackerStore
from rasa.shared.core.domain import Domain
import asyncio
import yaml
app = Flask(__name__)

log_file = 'logs/agent.log'
logging.basicConfig(filename=log_file, level=logging.INFO)
logger = logging.getLogger(__name__)

class Bot:
    def __init__(self, model_path, config_path, domain_path):
        with open(config_path, 'r') as config_file:
            config = yaml.safe_load(config_file)

        # Get the necessary configuration values
        endpoint_url = config['endpoints']['api_url']
        db_host = config['database']['host']
        db_port = config['database']['port']
        db_username = config['database']['username']
        db_password = config['database']['password']
        db_name = config['database']['database_name']

        # Set up the endpoint and tracker store
        endpoint = EndpointConfig(url=endpoint_url)
        tracker_store = SQLTrackerStore(
            dialect="postgresql",
            host=db_host,
            port=db_port,
            username=db_username,
            password=db_password,
            db=db_name
        )

        self.agent = Agent.load(model_path, action_endpoint=endpoint, tracker_store=tracker_store, domain=domain_path)

    async def get_response(self, user_message, sender_id):
        parsed = await self.agent.parse_message(user_message)
        intent = parsed['intent']['name']
        confidence = parsed['intent']['confidence']
        response = await self.agent.handle_text(user_message, sender_id=sender_id)
        result = {'text': response, 'intent': parsed}

        return result

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data['message']
        sender_id = data['sender_id']
        skill_id = data['skill_id']

        model_path = f"skills/{skill_id}/models/"
        config_path = "input/db_config.yml"
        domain_path = f"skills/{skill_id}/domain.yml"
        domain = Domain.load(domain_path)

        if not os.path.exists(model_path) or not os.path.isfile(domain_path):
            logger.error(f"Invalid skill_id: {skill_id}")
            return jsonify({'error': 'Invalid skill_id'})

        bot = Bot(model_path, config_path, domain)
        response = asyncio.run(bot.get_response(user_message, sender_id))
        return jsonify(response)
    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")
        return jsonify({'error': 'An error occurred'})


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5007)

