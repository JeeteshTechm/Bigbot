from contrib.application import OAuthProvider
from requests_oauthlib import OAuth2Session
from contrib.application import SkillProvider
from contrib.application import Descriptor
from django.template import Context, Template

from collections import defaultdict
import json, requests, random, datetime, uuid

import xmlrpc.client


class OdooApiOAuthProvider(OAuthProvider):

    def __init__(self):
        super(OdooApiOAuthProvider, self).__init__()

    def authorization_url(self, scope, redirect_uri, settings):
        return redirect_uri

    def is_scope_authorized(self, oauth, scope):
        pass

    def fetch_token(self, scope, redirect_uri, settings, authorization_response, *args, **kwargs):
        return uuid.id().hex

    def build_oauth(self, token):
        pass



class OdooApiSkillProvider(SkillProvider):
    def __init__(self):
        self.oauth_component = 'apps.odooapi.component.OdooApiOAuthProvider'
        self.scope = []

        super().__init__(Descriptor('test.Descriptor'))


    def auth_providers(self, package, user, *args, **kwargs):
        return [] #[OAuthProvider.get(self.oauth_component, user, self.scope)]

    def on_execute(self, package, user, data, *args, **kwargs):
        result = defaultdict()

        result["action_type"] = data["action_type"]
        result["executed"] = True
        #
        # Get Server Version
        #

        if data["action_type"] == "check_version":

            try:
                common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(data["host"]))
                response = common.version()
                result["server_version"] = response["server_version"]
                result["error"] = False
                return result
            except:
                result["server_version"] = ""
                result["error"] = True
                result["error_msg"] = "Error occurred. Please recheck the server url and credentialsi"
                return result

        #
        # Test Connection to DB
        #

        if data["action_type"] == "check_connection":

            host = data["host"]
            dbname = data["dbname"]
            username = data["username"]
            password = data["password"]

            status, conn_str, uid = self.__connect(host, dbname, username, password)

            print(status, conn_str, uid)

            if not status:
                result["error"] = True
                result["error_msg"] = "Error occurred. Please enter the correct url, database name and credentials"
                return result

            result["error"] = False
            return result

        #
        # CHECK ACCESS WRITES TO TABLE/MODEL
        #

        if data["action_type"] == "check_access_rights":

            host = data["host"]
            dbname = data["dbname"]
            username = data["username"]
            password = data["password"]

            if data["access_types"] == 1 :
                access_types = ['read']
            elif data["access_types"] == 2 :
                access_types = ['write']
            else:
                access_types = ["read", "write"]


            status, conn_str, uid = self.__connect(host, dbname, username, password)

            if not status:
                result["error"] = True
                result["error_msg"] = "Error occurred. Please enter the correct url, database name and credentials"
                return result

            ret = conn_str.execute_kw(dbname, uid, password, data["model"], 'check_access_rights', access_types, {'raise_exception': False})

            result["error"] = False
            result["access_rights"] = ret
            return result


        #
        # SEARCH AND READ
        #


        if data["action_type"] == "search_read":

            host = data["host"]
            dbname = data["dbname"]
            username = data["username"]
            password = data["password"]

            status, conn_str, uid = self.__connect(host, dbname, username, password)

            if not status:
                result["error"] = True
                result["error_msg"] = "Error occurred. Please enter the correct url, database name and credentials"
                return result

            if data["limit"] == "":
                data["limit"] = 10

            #  query filters ['is_company', '=', True]
            # fields : column names
            # limit :

            ret = conn_str.execute_kw(dbname, uid, password, data["model"], 'search_read', [[]], {'fields': data["column_names"], 'limit': data["limit"]})
            result["data"] = ret
            result["column_names"] = data["column_names"]
            result["model"] = data["model"]
            result["query"] = data["query"]
            result["limit"] = data["limit"]

            print(ret)

        return result

    #
    #
    #
    def build_text(self, package, user, content, result, *args, **kwargs):
        input = kwargs.get('input')

        t = Template(content)
        c = Context({"user": user, "result":result, "input":input})
        output = t.render(c)
        return output

    #
    #
    #
    def build_result(self, package, user, node, result, *args, **kwargs):
        input = kwargs.get('input')

        if node['node'] == 'big.bot.core.text':
            t = Template(node['content'])
            c = Context({"user": user, "result":result, "input":input})
            output = t.render(c)
            return output

    #
    #
    #
    def __connect(self, url, dbname, username, password):
        uid = None
        models_conn = None

        try:
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
            uid = common.authenticate(dbname, username, password, {})

            models_conn = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

            return True, models_conn, uid
        except:
            return False, models_conn, uid

