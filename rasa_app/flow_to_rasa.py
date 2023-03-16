import rasa
import networkx as nx

# Load the trained Rasa model
model_path = "path/to/your/model"
interpreter = rasa.shared.nlu.interpreter.Interpreter.load(model_path)

# Define a function to convert a flow into Rasa Training Data
def convert_flow_to_training_data(flow):
    training_data = {"common_examples": []}
    for block in flow.blocks:
        # Extract the tags associated with the block
        tags = block.tags

        # Extract the properties associated with the block
        properties = block.properties

        # Create an intent label based on the tags
        intent_label = "_".join(tags)

        # Create an entity label based on the properties
        entity_label = " ".join([f"{key}:{value}" for key, value in properties.items()])

        # Generate training examples based on the input and output properties of the block
        input_example = block.input_property
        output_example = block.output_property

        # Add the training examples to the training data
        training_data["common_examples"].append({"text": input_example, "intent": intent_label, "entities": [{"start": 0, "end": len(entity_label), "value": entity_label, "entity": "property"}]})
        training_data["common_examples"].append({"text": output_example, "intent": intent_label, "entities": [{"start": 0, "end": len(entity_label), "value": entity_label, "entity": "property"}]})

    return training_data

# Define a function to convert a flow into Rasa stories
def convert_flow_to_stories(flow):
    stories = []
    for i in range(len(flow.blocks)-1):
        current_block = flow.blocks[i]
        next_block = flow.blocks[i+1]
        input_property = current_block.output_property
        output_property = next_block.input_property
        intent_label = "_".join(current_block.tags)
        story = f"""
        ## {intent_label}
        * {intent_label}
            - slot{{"input_property": "{input_property}", "output_property": "{output_property}"}}
            - {next_block.input_property}
        """
        stories.append(story)
    return stories

# Define a function to recognize intents in real-time and handle transitions between blocks
def recognize_intent(text, tracker):
    # Use the Rasa interpreter to parse the user's input and extract intent and entities
    result = interpreter.parse(text)

    # Get the intent label and confidence score
    intent = result["intent"]["name"]
    confidence = result["intent"]["confidence"]

    # Use the intent label and current slot values to query the Rasa stories and return the next action
    next_action = get_next_action(intent, tracker)

    return next_action, confidence

# Define a function to query the Rasa stories and return the next action
def get_next_action(intent, tracker):
    # Use the Rasa tracker to get the current slot values
    input_property = tracker.get_slot("input_property")
    output_property = tracker.get_slot("output_property")

    # Define a list of Rasa stories based on the intent and current slot values
    # You can define these stories programmatically based on the structure of your flows and blocks
    # Use the input and output properties to fill in the slot values in the stories
    stories = [
        f"""
        ## {intent}
        * {intent}
            - slot{{"input_property": "{input_property}", "output_property": "{output_property}"}}
            - action_{i}
        """ for i in range(1, 6)
    ]

    # Use the Rasa Core engine to predict the next action based on the available stories
    next_action = rasa.core.agent.load_local_model().predict_next_action(tracker, stories)

    return next_action



# rasa train core -s data/stories -d data/domain.yml -o models/core
