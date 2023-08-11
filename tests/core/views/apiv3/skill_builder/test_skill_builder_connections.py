import pytest
from django.test import Client
from unittest.mock import patch, MagicMock
from main import Binder

@pytest.fixture  
def api_client():
    return Client()

def get_connection_value(key):
    dict = {
        "main.Block.PromptBinary" : [[1, 'Next']],
        "main.Block.PromptChatPlatform" : [[1, 'Next']],
        "main.Block.PromptDuration" : [[1, 'Next']],
        "main.Block.PromptImage" : [[1, 'Next']],
        "main.Block.PromptPayment" : [[1, 'Next']],
        "main.Block.PromptPreview" : [[1, 'Next']],
        "main.Block.PromptText" : [[1, 'Next']],
        "main.Block.DecisionBlock" : [[1, 'Next'], [-1, 'Reject']],
        "main.Block.InputDate" : [[1, 'Next'], [-1, 'Reject']],
        "main.Block.InputDateTime" : [[1, 'Next'], [-1, 'Reject']],
        "main.Block.InputDuration" : [[1, 'Next'], [-1, 'Reject']],
        "main.Block.InputEmail" : [[1, 'Next'], [-1, 'Reject']],
        "main.Block.InputFile" : [[1, 'Next'], [-1, 'Reject']],
        "main.Block.InputNumber" : [[1, 'Next'], [-1, 'Reject']],
        "main.Block.InputOAuth" : [[1, 'Next'], [-1, 'Reject']],
        "main.Block.InputPayment" : [[1, 'Next'], [-1, 'Reject']],
        "main.Block.InputSearchable" : [[1, 'Next'], [-1, 'Reject']],
        "main.Block.InputSkill" : [[1, 'Next'], [-1, 'Reject']],
        "main.Block.InputText" : [[1, 'Next'], [-1, 'Reject']],
        "main.Block.InterpreterSkill" : [[1, 'Next'], [2, 'Reject']],
        "main.Block.DataExchange" : [[1, 'Next'], [2, 'Reject']],
        "main.Block.TerminalBlock" : [],
    }
    return dict[key]

def test_empty_component(api_client):
    url = "/api/v3/skill/builder/connections"
    response = api_client.get(url)
    assert response.status_code == 200
    response = response.json().get("result")
    assert response == None

def test_prompt_binary(api_client):
    component="main.Block.PromptBinary"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_prompt_chat_platform(api_client):
    component="main.Block.PromptChatPlatform"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_prompt_image(api_client):
    component="main.Block.PromptImage"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_prompt_payment(api_client):
    component="main.Block.PromptPayment"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_promt_preview(api_client):
    component="main.Block.PromptPreview"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_prompt_text(api_client):
    component="main.Block.PromptText"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_decision_block(api_client):
    component="main.Block.DecisionBlock"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_input_date(api_client):
    component="main.Block.InputDate"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_input_datetime(api_client):
    component="main.Block.InputDateTime"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_input_duration(api_client):
    component="main.Block.InputDuration"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_input_email(api_client):
    component="main.Block.InputEmail"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_input_file(api_client):
    component="main.Block.InputFile"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_input_number(api_client):
    component="main.Block.InputNumber"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_input_oauth(api_client):
    component="main.Block.InputOAuth"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_input_payment(api_client):
    component="main.Block.InputPayment"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_input_searchable(api_client):
    component="main.Block.InputSearchable"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_input_skill(api_client):
    component="main.Block.InputSkill"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_input_text(api_client):
    component="main.Block.InputText"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_interpreter_skill(api_client):
    component="main.Block.InterpreterSkill"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_data_exchange(api_client):
    component="main.Block.DataExchange"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)

def test_terminal_block(api_client):
    component="main.Block.TerminalBlock"
    url = f"/api/v3/skill/builder/connections?component={component}"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json().get("result") == get_connection_value(component)
