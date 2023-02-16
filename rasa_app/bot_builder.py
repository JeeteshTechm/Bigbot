import json
import os
import uuid

from rasa.cli.scaffold import create_initial_project
from rasa.model import get_model
from rasa.core.agent import Agent
from rasa.utils.endpoints import EndpointConfig
from rasa.core.interpreter import RasaNLUInterpreter
from rasa.core.policies.fallback import FallbackPolicy
from rasa.core.policies.keras_policy import KerasPolicy
from rasa.core.policies.memoization import MemoizationPolicy

from django.http import JsonResponse, HttpResponseBadRequest

def create_bot(request):
    # Load the request payload
    payload = json.loads(request.body)

    # Extract the required parameters from the payload
    bot_id = payload.get("bot_id")
    message = payload.get("message")
    intents = payload.get("intents")
    entities = payload.get("entities")

    # Generate a unique ID for the bot's project directory
    project_id = uuid.uuid4().hex

    # Create a new Rasa project in the rasa_models directory
    project_path = os.path.join("rasa_models", project_id)
    create_initial_project(project_path)

    # Create a new domain.yml file for the bot
    domain_file = os.path.join(project_path, "domain.yml")
    with open(domain_file, "w") as f:
        f.write("intents:\n")
        for intent in intents:
            f.write("  - {}\n".format(intent["name"]))

        f.write("\nentities:\n")
        for entity in entities:
            f.write("  {}:\n".format(entity["name"]))
            f.write("  - {}\n".format(entity["value"]))

    # Train the Rasa model for the bot
    model_directory = get_model(project_path)
    agent = Agent.load(model_directory, interpreter=RasaNLUInterpreter(model_directory))
    training_data = agent.load_data_from_domain(domain_file)

    agent.train(training_data)
    agent.persist(model_directory)

    # Configure the bot's endpoint
    endpoint_config = EndpointConfig(url="http://localhost:5005/webhooks/rest/webhook")

    fallback = FallbackPolicy(fallback_action_name="utter_unclear",
                              core_threshold=0.2,
                              nlu_threshold=0.1)
    keras_policy = KerasPolicy(max_history=5)
    memo_policy = MemoizationPolicy(max_history=5)

    # Create a new Rasa agent for the bot
    rasa_agent = Agent.load(model_directory, policies=[memo_policy, fallback, keras_policy], interpreter=RasaNLUInterpreter(model_directory), action_endpoint=endpoint_config)

    # Store the bot's agent in a dictionary for later retrieval
    bots[bot_id] = rasa_agent

    return JsonResponse({"message": "Bot created successfully"})


def chatbot(bot_id, message):
    # Find the latest trained model for the bot
    models_dir = "rasa_models"
    model_names = [f for f in os.listdir(models_dir) if bot_id in f]
    if not model_names:
        raise ValueError(f"No trained models found for bot '{bot_id}'")

    latest_model_name = sorted(model_names)[-1]
    model_path = os.path.join(models_dir, latest_model_name)

    # Create the Rasa agent with the latest trained model
    endpoint_config = EndpointConfig(url="http://localhost:5055/webhook")
    interpreter = RasaNLUInterpreter(model_path)
    agent = Agent.load(model_path, interpreter=interpreter, action_endpoint=endpoint_config)

    # Parse the user message and get the bot's response
    response = agent.handle_text(message)

    return response
