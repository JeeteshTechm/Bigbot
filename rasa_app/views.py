from bot_builder import create_bot, chatbot

from django.http import JsonResponse
from bot_builder import create_bot, chatbot

def create_bot_view(request):
    # Extract the data from the request body
    data = request.POST

    # Call the create_bot function to create a new bot
    bot_id = data.get('bot_id')
    message = data.get('message')
    intents = data.get('intents')
    entities = data.get('entities')
    create_bot(bot_id, message, intents, entities)

    # Return a JSON response indicating success
    response_data = {'success': True}
    return JsonResponse(response_data)

def chat_view(request):
    # Extract the data from the request body
    data = request.POST

    # Call the chatbot function to chat with the specified bot
    bot_id = data.get('bot_id')
    message = data.get('message')
    response = chatbot(bot_id, message)

    # Return the response as a JSON object
    response_data = {'response': response}
    return JsonResponse(response_data)
