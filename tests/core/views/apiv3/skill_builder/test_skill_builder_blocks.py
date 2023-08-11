import pytest

from django.test import Client

from unittest.mock import patch, MagicMock
from main import Binder


@pytest.fixture  
def api_client():
    return Client()

@pytest.fixture
def mock_registry():
    registry = MagicMock(spec=Binder.Registry)
    registry.blocks = [MockBlock1, MockBlock2]
    return registry

@pytest.fixture
def mock_registry_empty():
    registry = MagicMock(spec=Binder.Registry)
    registry.blocks = []
    return registry

class MockBlock1:
    def __init__(self, context, id, properties, connections):
        pass
    def serialize(self):
        return {'name': 'MockBlock1'}

class MockBlock2:
    def __init__(self, context, id, properties, connections):
        pass
    def serialize(self):
        return {'name': 'MockBlock2'}

@patch.object(Binder, 'Registry')
def test_skill_builder_blocks(mock_get_blocks, mock_registry, api_client):
    mock_get_blocks.return_value = mock_registry
    url = "/api/v3/skill/builder/blocks"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json() == {'id': None, 'jsonrpc': '2.0', 'result': [{'name': 'MockBlock1'}, {'name': 'MockBlock2'}]}

@patch.object(Binder, 'Registry')
def test_skill_builder_empty(mock_get_blocks, mock_registry_empty, api_client):
    mock_get_blocks.return_value = mock_registry_empty
    url = "/api/v3/skill/builder/blocks"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json() == {'id': None, 'jsonrpc': '2.0', 'result': []}

def test_skill_builder_blocks_classes(api_client):
    url = "/api/v3/skill/builder/blocks"
    response = api_client.get(url)
    assert response.status_code == 200
    assert len(response.json().get("result")) == 25

def test_prompt_binary(api_client):
    url = "/api/v3/skill/builder/blocks"
    response = api_client.get(url)
    response_json = response.json().get("result")
    promptBinary = [i for i in response_json if i.get('component')=='main.Block.PromptBinary'][0]
    expected_description = {'name': 'Binary', 'summary': 'No description available', 'category': 'prompt'}
    assert promptBinary.get("descriptor") == expected_description
