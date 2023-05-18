import requests
import json

# Define the URL of your Rasa server
rasa_url = "http://localhost:5005/webhooks/rest/webhook"

# Define the URL of your Dialogueflow agent webhook
delegate_url = "https://delegate-agent-webhook-url.com"

def handle_delegate_request(request):
    # Extract the user input and session ID from the request
    user_input = request.get("queryResult").get("queryText")
    session_id = request.get("session")

    # Send the user input and session ID to the Rasa server
    rasa_response = requests.post(rasa_url, json={"message": user_input, "session_id": session_id}).json()

    # Check if the Rasa response requires more information from the user
    if rasa_response[0].get("next_action") == "action_listen":
        # If so, send a request to Dialogueflow to continue the conversation
        delegate_request = {
            "queryInput": {
                "text": {
                    "text": user_input,
                    "languageCode": "en-US"
                }
            },
            "session": session_id
        }

        delegate_response = requests.post(delegate_url, json=delegate_request).json()

        # Extract the user input and session ID from the Dialogueflow response
        user_input = delegate_response.get("queryResult").get("queryText")
        session_id = delegate_response.get("session")

        # Send the user input and session ID to the Rasa server again
        rasa_response = requests.post(rasa_url, json={"message": user_input, "session_id": session_id}).json()

    # Check if the skill session should be terminated
    should_escape = rasa_response[0].get("should_escape")

    if should_escape:
        # If so, send a request to Dialogueflow to end the current session
        delegate_request = {
            "queryInput": {
                "event": {
                    "name": "SKILL_ESCAPED",
                    "languageCode": "en-US"
                }
            },
            "session": session_id
        }

        requests.post(delegate_url, json=delegate_request)

    # Extract the response text and any additional data
    response_text = rasa_response[0].get("text")
    response_data = rasa_response[0].get("data")

    # Construct the response for Dialogueflow
    delegate_response = {
        "fulfillmentText": response_text,
        "payload": response_data,
        "outputContexts": [{"name": session_id}]
    }

    return delegate_response
