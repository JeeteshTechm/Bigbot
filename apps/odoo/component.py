import json
import math
import urllib.parse as urlparse

import requests
from requests_oauthlib import OAuth2Session

from main.Component import OAuthProvider, SkillProvider
from main.Node import SearchNode

from .icon import icon


def float2hours(time):
    hours = math.floor(time)
    minutes = math.floor((time - hours) * 60)

    if minutes < 10:
        minutes = f"0{minutes}"

    return f"{hours}:{minutes}"


class OdooOAuthProvider(OAuthProvider):
    def __init__(self, config):
        self.AUTH_URL = "connect"
        self.TOKEN_URL = "token"
        self.CLIENT_ID = self.get_variable("com.big.bot.odoo", "CLIENT_ID")
        self.CLIENT_SECRET = self.get_variable("com.big.bot.odoo", "CLIENT_SECRET")
        self.SCOPE = []
        super(OdooOAuthProvider, self).__init__(config)
        self.update_meta(
            {
                "icon": icon,
                "title": "Odoo",
                "description": "You need to authorize your account first.",
            }
        )

    def authorization_url(self, redirect_uri, user_id, **kwargs):
        url = self.get_variable("com.big.bot.odoo", "TOKEN_URL")
        query = urlparse.urlencode({"redirect_uri": redirect_uri})
        return f"{url}?{query}"

    def build_oauth(self, token):
        data_endpoint = self.get_variable("com.big.bot.odoo", "DATA_ENDPOINT")
        oauth_object = OdooOauthObject(data_endpoint, token)
        return oauth_object

    def fetch_token(self, redirect_uri, authorization_response, **kwargs):
        url_parts = urlparse.urlparse(authorization_response)
        query = dict(urlparse.parse_qsl(url_parts.query))
        return query["access_token"]

    def is_authorized(self, oauth, **kwargs):
        return True

    def is_expired(self, user_id, token, **kwargs):
        return False

    def refresh_token(self, user_id, token, **kwargs):
        return token


class OdooSkillProvider(SkillProvider):
    def on_execute(self, binder, user_id, package, data, **kwargs):
        # Preprocess data before making request to Odoo
        if package == "com.bits.odoo.create.timesheet":
            unit_amount = data["unit_amount"]
            time = 0
            for index, num in enumerate(unit_amount):
                if index == 0:
                    time += num
                else:
                    time += num / (60 ** index)
                    data["unit_amount"] = time

        # Odoo request
        oauth = self.oauth(binder, user_id, OdooOAuthProvider)
        response = oauth.post(package=package, method="execute_skill", values=data)
        result = response.json()

        # "Beautify" data for jinja
        if package == "com.bits.odoo.create.timesheet":
            result["result"]["object__account_analytic_line"]["unit_amount"] = float2hours(
                result["result"]["object__account_analytic_line"]["unit_amount"]
            )

        if "error" in result and result["error"]:
            return None
        return result["result"]

    def on_search(self, binder, user_id, package, searchable, query, **kwargs):
        print("searchable =>", searchable)
        model = searchable.property_value("model")
        oauth = self.oauth(binder, user_id, OdooOAuthProvider)
        items = []
        result = oauth.post(
            package=package, method="name_search", query=query, model=model, domain=[]
        ).json()["result"]
        for item in result:
            items.append(SearchNode.wrap_text(item["name"], item["id"]))
        return items

    def on_query_search(self, binder, user_id, package, searchable, query, **kwargs):
        model = searchable.property_value("model")
        oauth = self.oauth(binder, user_id, OdooOAuthProvider)
        result = oauth.post(
            package=package, method="name_search", query=query, model=model, domain=[]
        ).json()["result"]
        print(result)
        print("===================")
        print("===================")
        print("===================")
        print("===================")

        if len(result) == 1:
            return result[0]["id"]
        pass


class OdooOauthObject:
    def __init__(self, data_endpoint, token):
        self.data_endpoint = data_endpoint
        self.token = token

    def post(self, **kwargs):
        object = {
            "token": self.token,
        }
        object.update(kwargs)
        return requests.post(url=self.data_endpoint, data={"data": json.dumps(object)})

    # post(package=package, values = data)
    # execute_skill
    # name_search
