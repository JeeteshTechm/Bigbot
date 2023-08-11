import pytest
from django.test import Client
from unittest.mock import patch, MagicMock
from main import Binder

@pytest.fixture  
def api_client():
    return Client()

def test_all_nodes(api_client):
    url = "/api/v3/skill/builder/nodes"
    response = api_client.get(url)
    assert response.status_code == 200
    assert len(response.json().get("result")) == 13

def test_node_core_payment(api_client):
    url = "/api/v3/skill/builder/nodes"
    response = api_client.get(url)
    response_json = response.json().get("result")
    payment_meta = [i.get("meta") for i in response_json if i.get('node')=='big.bot.core.payment'][0]
    expected_payment_meta = {
                "charge_summary": "You have to pay",
                "currency_code": "USD",
                "currency_symbol": "$",
                "button_text": "Make Payment",
                "payment_services": [
                    {
                        "name": "Bank Card",
                        "icon": "https://cdn.worldvectorlogo.com/logos/apple-pay.svg",
                        "payment_url": "https://razorpay.com/?version=t1"
                    },
                    {
                        "name": "Google Pay",
                        "icon": "https://cdn.worldvectorlogo.com/logos/apple-pay.svg",
                        "payment_url": "https://razorpay.com/?version=t1"
                    },
                    {
                        "name": "Apple Pay",
                        "icon": "https://cdn.worldvectorlogo.com/logos/apple-pay.svg",
                        "payment_url": "https://razorpay.com/?version=t1"
                    }
                ]
            }
    assert payment_meta == expected_payment_meta

