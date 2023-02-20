##source:ChatGpt

import os
import yaml
from rasa.agent import Agent
from rasa.core.interpreter import RegexInterpreter
from rasa.core.policies import MemoizationPolicy, FormPolicy
from rasa.core.policies.fallback import FallbackPolicy
from rasa.core.policies.rule_based import RuleBasedPolicy
from rasa.nlu import config as nlu_config
from rasa.nlu.model import Trainer
from rasa.nlu.components import ComponentBuilder
from rasa.nlu.tokenizers.whitespace_tokenizer import WhitespaceTokenizer
from rasa.nlu.featurizers.sparse_featurizer.regex_featurizer import RegexFeaturizer
from rasa.nlu.featurizers.sparse_featurizer.count_vectors_featurizer import CountVectorsFeaturizer
from rasa.nlu.featurizers.sparse_featurizer.tfidf_featurizer import TfidfFeaturizer
from rasa.nlu.classifiers.diet_classifier import DIETClassifier
from rasa.utils.endpoints import EndpointConfig

from django.http import JsonResponse, HttpResponseBadRequest


def create_bot(bot_id, payload):
    # Define the file paths
    models_dir = "rasa_models"
    if not os.path.exists(models_dir):
        os.makedirs(models_dir)
    bot_models_dir = os.path.join(models_dir, bot_id)
    if not os.path.exists(bot_models_dir):
        os.makedirs(bot_models_dir)
    domain_path = os.path.join(bot_models_dir, "domain.yml")
    nlu_path = os.path.join(bot_models_dir, "nlu")
    stories_path = os.path.join(bot_models_dir, "stories.md")
    config_path = os.path.join(bot_models_dir, "config.yml")

    # Define the domain file
    domain = {"intents": {}, "entities": {}}

    # Define the intent and entity lists from the payload
    intents = payload.get("intents", [])
    entities = payload.get("entities", [])

    # Add the intents to the domain file
    for intent in intents:
        intent_name = intent.get("name")
        intent_examples = intent.get("examples", [])

        domain["intents"][intent_name] = {"use_entities": True, "responses": {}}

        if intent_examples:
            domain["intents"][intent_name]["examples"] = []
            for example in intent_examples:
                domain["intents"][intent_name]["examples"].append({"text": example})

    # Add the entities to the domain file
    for entity in entities:
        entity_name = entity.get("name")
        domain["entities"][entity_name] = {}

    # Save the domain file
    with open(domain_path, "w") as f:
        yaml.dump(domain, f)

    # Train the NLU model
    builder = ComponentBuilder(use_cache=True)
    builder.add_component(RegexFeaturizer())
    builder.add_component(TfidfFeaturizer())
    builder.add_component(CountVectorsFeaturizer())
    builder.add_component(WhitespaceTokenizer())
    builder.add_component(DIETClassifier.create(nlu_config.load("config.yml")))
    trainer = Trainer(builder)

    training_data_dir = "training_data"
    nlu_file = os.path.join(training_data_dir, "nlu.md")
    stories_file = os.path.join(training_data_dir, "stories.md")
    rules_file = os.path.join(training_data_dir, "rules.yml")

    training_data = trainer.load_data(nlu_file)
    interpreter = trainer.train(training_data)
    interpreter.persist(bot_models_dir)

    # Define the agent
    endpoint_config = EndpointConfig(url="http://18.136.204.25:5056/webhook")
    agent = Agent(
        domain=domain_path,
        policies=[
            RuleBasedPolicy(),
            FallbackPolicy(),
            MemoizationPolicy(),
            FormPolicy(),
        ],
        interpreter=interpreter,
        action_endpoint=endpoint_config,
    )

    # Train the Core model
    training_data = agent.load_data(
        stories_file=stories_file,
        nlu_data=nlu_file,
        rules=rules_file,
    )
    agent.train(training_data)

    # Save the agent
    agent.persist(bot_models_dir)

    return agent

def chatbot(bot_id, message):
    # Check if a trained model already exists for the bot
    models_dir = "rasa_models"
    model_names = [f for f in os.listdir(models_dir) if bot_id in f]
    if model_names:
        latest_model_name = sorted(model_names)[-1]
        model_path = os.path.join(models_dir, latest_model_name)

        # Load the Rasa agent with the latest trained model
        endpoint_config = EndpointConfig(url="http://18.136.204.25:5056/webhook")
        interpreter = RasaNLUInterpreter(model_path)
        agent = Agent.load(model_path, interpreter=interpreter, action_endpoint=endpoint_config)
    else:
        # Create a new bot model with the given bot_id
        payload = get_bot_payload_from_db(bot_id)  # retrieve bot data from database
        agent = create_bot(bot_id, payload)

    # Parse the user message and get the bot's response
    response = agent.handle_text(message)

    return response

