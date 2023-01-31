from main.Component import OAuthProvider,SkillProvider
from main.Statement import OutputStatement
from requests_oauthlib import OAuth2Session
from django.template import Context, Template
from requests_oauthlib import OAuth2Session
import requests
from jose import jws as jose_jws
import json
import math
from django.conf import settings as django_settings
import datetime
from urllib import parse as urlparse
from core.models import OAuthTokenModel

from .node import Expandable
from .utils import number_to_ordinal

class MyinfoOAuthProvider(OAuthProvider):
    def __init__(self,config):
        self.CLIENT_ID = self.get_variable("com.big.bot.myinfo","CLIENT_ID")
        # self.CLIENT_ID = 'STG2-MYINFO-SELF-TEST'
        self.CLIENT_SECRET = self.get_variable("com.big.bot.myinfo", "CLIENT_SECRET")
        # self.CLIENT_SECRET = '44d953c796cccebcec9bdc826852857ab412fbe2'
        self.AUTH_URL = 'https://sandbox.api.myinfo.gov.sg/com/v3/authorise'
        self.TOKEN_URL = 'https://sandbox.api.myinfo.gov.sg/com/v3/token'
        self.scope = []
        super().__init__(config)
        self.update_meta(
            {
                "icon": "",
                "title": "Myinfo",
                "description": "You need to authorize your account first.",
            }
        )

    def authorization_url(self, redirect_uri, user_id, **kwargs):
        aad_auth = OAuth2Session(client_id=self.CLIENT_ID,
                                 redirect_uri=redirect_uri)
        sign_in_url, state = aad_auth.authorization_url(
            self.AUTH_URL,
            attributes=','.join(self.scope),
            purpose="BigBot"
        )
        return sign_in_url

    def is_authorized(self, oauth, **kwargs):
        req = oauth.get(self.TOKEN_URL)
        if req.status_code == 200:
            return True
        return False

    def is_scope_authorized(self, oauth, scope):
        return True

    def _get_redirect_uri(self):
        return 'http://localhost:3001/callback'

    def fetch_token(self, redirect_uri, authorization_response, *args, **kwargs):
        cacheCtl = "no-cache"
        contentType = "application/x-www-form-urlencoded"
        url = self.TOKEN_URL
        request = kwargs.get('request')
        code = request.GET["code"]
        params = {}
        params['grant_type'] = 'authorization_code'
        params['code'] = code
        params['redirect_uri'] = redirect_uri
        params['client_id'] = self.CLIENT_ID
        params['client_secret'] = self.CLIENT_SECRET

        headers = dict()
        headers['Content-Type'] = contentType
        headers['Cache-Control'] = cacheCtl

        body = requests.post(url, data=params, headers=headers).json()
        token = {
            'main_token': body,
            'access_token':body.get('access_token'),
        }

        file_path = django_settings.BASE_DIR + "/apps/myinfo/ssl/staging_myinfo_public_cert.cer"
        payload = self.verify_jws(token['access_token'], file_path)

        token['uinfin'] = payload['sub']
        token['exp'] = payload['exp']

        return token

    def verify_jws(self, token, publicCert):
        pemfile = open(publicCert, 'r')
        keystring = pemfile.read()
        pemfile.close()
        payload = jose_jws.verify(str(token), str(keystring),  algorithms=['RS256'])
        payload = json.loads(payload.decode('utf8'))

        return payload

    def build_oauth(self, token):
        return OAuth2Session(token=token)

    def is_expired(self,user_id, token, **kwargs):
        if int(token["exp"]) < datetime.datetime.now().timestamp():
            return True
        return False

    def refresh_token(self, user_id, token, **kwargs):
        refresh_url = self.TOKEN_URL
        extra = {
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET,
        }
        myinfo = OAuth2Session(self.CLIENT_ID, token=token)
        return myinfo.refresh_token(refresh_url, **extra)


class MyInfo(SkillProvider):

    def __init__(self, config):
        self.items = [["name","Name"],["sex","Sex"],["race","Race"],["nationality","Nationality"],["dob","Dob"],
                      ["email","Email"],["mobileno","Mobileno"],["regadd","Regadd"],["housingtype","Housingtype"],
                      ["hdbtype","Hdbtype"],["marital","Marital"],["edulevel","Edulevel"],["ownerprivate","Ownerprivate"],
                      ["cpfcontributions","Cpfcontributions"],["cpfbalances","Cpfbalances"]
                      ]
        self.scope = []
        self.myInfoComponent = "apps.myinfo.component.MyinfoOAuthProvider"
        super().__init__(config)

    def on_execute(self,binder, user_id,package, data, *args, **kwargs):
        OAuthProvider.clear_token(self.auth_providers, user_id)
        return {}

    def on_search(self, binder, user_id, package, searchable, query, *args, **kwargs):
        saved_data = kwargs.get('data')
        data = [self.create_search_item('Submit',"\()")]
        for item in [i for i in  self.items if query in i[0]] if query else self.items:
            if saved_data and 'fields' in saved_data:
                if item[0] in saved_data['fields']:
                    continue
            data.append(self.create_search_item(item[1],item[0]))
        return data

class MyInfoPost(SkillProvider):

    def __init__(self,config):
        self.oauth_component= 'apps.myinfo.component.MyinfoOAuthProvider'
        self.items = [["name","Name"],["sex","Sex"],["race","Race"],["nationality","Nationality"],["dob","Dob"],
                      ["email","Email"],["mobileno","Mobileno"],["regadd","Regadd"],["housingtype","Housingtype"],
                      ["hdbtype","Hdbtype"],["marital","Marital"],["edulevel","Edulevel"],["ownerprivate","Ownerprivate"],
                      ["cpfcontributions","Cpfcontributions"],["cpfbalances","Cpfbalances"]
                      ]
        self.scope = ["name","sex","race","nationality","dob","email","mobileno","regadd",
                 "housingtype","hdbtype","marital","edulevel","ownerprivate","cpfcontributions","cpfbalances"]
        super().__init__(config)


    def auth_providers(self, package, user, *args, **kwargs):
        data = kwargs.get('data')
        
        if data:
           scope = data.get('fields',scope)
        return [OAuthProvider.get(self.oauth_component, user, self.scope)]

    def on_execute(self, binder, user_id, package, data, *args, **kwargs):
        provider = self.get_provider(self.oauth_component, package, user_id)
        settings = provider.get_settings()

        token = provider._get_token()['access_token']
        uinfin = provider._get_token()['uinfin']

        res = self.person_request(uinfin, token, settings, data)
        res = res.json()
        if 'code' in res:
            return False
        show_fields = {}
        if 'fields' in data:
            for f in data["fields"]:
                for i in self.items:
                    if i[0] == f:
                        show_fields[i[1]] = self._normalize(res,f)
                        break
            #self._to_forms(res, data["fields"])
        else:
            all_fields = []
            for f in self.items:
                all_fields.append(f[0])
                show_fields[f[1]] = self._normalize(res,f[0])
            #self._to_forms(res, all_fields)

        str_list = []
        e_list = ['Email','Apartment Type']
        for k,v in show_fields.items():
            if k is not None and v is not None:
                if k in e_list:
                    str_list.append(k+": "+v)
                else:
                    str_list.append(k+": "+v.lower().capitalize() )
        res['summary'] = ', '.join(str_list)
        return res


    def person_request(self, uinfin, validToken, settings, data):
        scope = data.get('fields',["name","sex","race","nationality","dob","email","mobileno","regadd",
                                   "housingtype","hdbtype","marital","edulevel","ownerprivate","cpfcontributions","cpfbalances"])

        cacheCtl = "no-cache"
        params = {}
        headers = dict()
        url = "https://sandbox.api.myinfo.gov.sg/com/v3/person" + "/" + uinfin + "/"

        # assemble params for Person API
        params = dict()
        params['client_id'] = settings["MYINFO_APP_CLIENT_ID"]
        params['attributes'] = ','.join(scope)

        headers['Cache-Control'] = cacheCtl
        headers['Authorization'] =  "Bearer {}".format(validToken)

        res = requests.get(url, params=params, headers=headers)
        return res

    def on_search(self, binder, user_id, package, searchable, query, *args, **kwargs):
        saved_data = kwargs.get('data')
        data = [self.create_search_item('Submit',"\()")]
        for item in [i for i in  self.items if query in i[0]] if query else self.items:
            if saved_data and 'fields' in saved_data:
                if item[0] in saved_data['fields']:
                    continue
            data.append(self.create_search_item(item[1],item[0]))
        return data

    def build_result(self, package, user, node, result, *args, **kwargs):
        if node['node'] == 'apps.myinfo.component.Expandable':
            input = kwargs.get('input')
            if 'fields' in input and input['fields']:
                scopes_vals = {
                }
                print(input['fields'], '++++++', result)
                for item in input['fields']:
                    scopes_vals[item] = result[item]
                return scopes_vals
            return result
        return super().build_result(package, user, node, result, *args, **kwargs)

    def _normalize(self, data, key):
        if key=='name':
            return data["name"]["value"]
        elif key=='nationality':
            return data["nationality"]["desc"]
        elif key=='mobileno':
            return data["mobileno"]["prefix"]["value"]+data["mobileno"]["areacode"]["value"]+" "+data["mobileno"]["nbr"]["value"]
        elif key=='dob':
            return data["dob"]["value"]
        elif key=='email':
            return data["email"]["value"]
        elif key=='marital':
            return data["marital"]["desc"]
        elif key=='edulevel':
            return data["edulevel"]["classification"]
        elif key=='sex':
            return data["sex"]["desc"]
        elif key=='housingtype':
            return data["housingtype"]["classification"]
        elif key=='hdbtype':
            return data["hdbtype"]["desc"]

class MyInfoShare(SkillProvider):

    def __init__(self,config):
        self.scope = ["name","sex","race","nationality","dob","email","mobileno","regadd",
                 "housingtype","hdbtype","marital","edulevel","ownerprivate","cpfcontributions","cpfbalances"]
        super().__init__(config)

    def auth_providers(self, package, user, *args, **kwargs):
        return []

    def on_execute(self, binder, user_id, package, data, *args, **kwargs):
        result_extra=kwargs.get('result_extra')
        if data['is_share'] == '1':
            self._to_forms(result_extra,data.get('fields',self.scope))
            return {
                'shared':True
            }
        return {}

    def _to_forms(self, data, fields):
        form_id = '1FAIpQLScYlZQBOzmoo0LP4UMblKXXaFGo3wMZZbHQNKNSg1zRDTeeVg'
        url = 'https://docs.google.com/forms/d/e/{}/formResponse'.format(form_id)
        form_data = {'entry.1993940178':self._normalize(data,'name') if 'name' in fields else "",
                     'entry.1561076982':self._normalize(data,'nationality') if 'nationality' in fields else "",
                     'entry.775770744':self._normalize(data,'mobileno')if 'mobileno' in fields else "",
                     'entry.1964378733':self._normalize(data,'dob')if 'dob' in fields else "",
                     'entry.1565429249':self._normalize(data,'email')if 'email' in fields else "",
                     'entry.1271999883':self._normalize(data,'marital')if 'marital' in fields else "",
                     'entry.650507267':self._normalize(data,'edulevel')if 'edulevel' in fields else "",
                     'entry.1184488854':self._normalize(data,'sex')if 'sex' in fields else "",
                     'entry.122026694':self._normalize(data,'housingtype')if 'housingtype' in fields else "",
                     'entry.16017563':self._normalize(data,'hdbtype')if 'hdbtype' in fields else "",
                     'draftResponse':[],
                     'pageHistory':0
                     }
        user_agent = {'Referer':'https://docs.google.com/forms/d/e/{}/viewform','User-Agent': "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.52 Safari/537.36".format(form_id)}
        r = requests.post(url, data=form_data, headers=user_agent)
        return {}

    def _normalize(self, data, key):
        if key=='name':
            return data["name"]["value"]
        elif key=='nationality':
            return data["nationality"]["desc"]
        elif key=='mobileno':
            return data["mobileno"]["prefix"]["value"]+data["mobileno"]["areacode"]["value"]+" "+data["mobileno"]["nbr"]["value"]
        elif key=='dob':
            return data["dob"]["value"]
        elif key=='email':
            return data["email"]["value"]
        elif key=='marital':
            return data["marital"]["desc"]
        elif key=='edulevel':
            return data["edulevel"]["classification"]
        elif key=='sex':
            return data["sex"]["desc"]
        elif key=='housingtype':
            return data["housingtype"]["classification"]
        elif key=='hdbtype':
            return data["hdbtype"]["desc"]

class MyInfoPropertyOAuthProvider(MyinfoOAuthProvider):
    def __init__(self, config):
        super().__init__(config)
        self.scope = ["name", "hdbownership.address", "cpfbalances"]
    
    def is_authorized(self, oauth, **kwargs):
        return True

    def fetch_token(self, redirect_uri, authorization_response, *args, **kwargs):
        cacheCtl = "no-cache"
        contentType = "application/x-www-form-urlencoded"
        url = self.TOKEN_URL
        
        parsed = urlparse.urlparse(authorization_response)
        code = urlparse.parse_qs(parsed.query).get('code')
        params = {}
        params['grant_type'] = 'authorization_code'
        if code:
            params['code'] = code[0]
        params['redirect_uri'] = redirect_uri
        params['client_id'] = self.CLIENT_ID
        params['client_secret'] = self.CLIENT_SECRET

        headers = dict()
        headers['Content-Type'] = contentType
        headers['Cache-Control'] = cacheCtl

        body = requests.post(url, data=params, headers=headers).json()
        token = {
            'main_token': body,
            'access_token':body.get('access_token'),
        }

        file_path = django_settings.BASE_DIR + "/apps/myinfo/ssl/staging_myinfo_public_cert.cer"
        payload = self.verify_jws(token['access_token'], file_path)

        token['uinfin'] = payload['sub']
        token['exp'] = payload['exp']

        return token

class MyInfoProperty(SkillProvider):

    def __init__(self, config):
        self.oauth_component= 'apps.myinfo.component.MyInfoPropertyOAuthProvider'
        self.scope = ["name", "hdbownership", "cpfbalances"]
        # self.CLIENT_ID = "STG2-MYINFO-SELF-TEST"
        self.CLIENT_ID = self.get_variable("com.big.bot.myinfo","CLIENT_ID")
        super().__init__(config)

    def auth_providers(self, package, user, *args, **kwargs):
        return [OAuthProvider.get(self.oauth_component, user, self.scope)]

    def person_request(self, uinfin, validToken, settings, data):
        scope = data.get('fields', ["name","hdbownership.address","cpfbalances"])

        cacheCtl = "no-cache"
        params = {}
        headers = dict()
        url = "https://sandbox.api.myinfo.gov.sg/com/v3/person" + "/" + uinfin + "/"
        # url = "https://sandbox.api.myinfo.gov.sg/com/v3/person-sample" + "/" + uinfin + "/"

        # assemble params for Person API
        params = dict()
        params['client_id'] = settings["CLIENT_ID"]
        params['attributes'] = ','.join(scope)

        headers['Cache-Control'] = cacheCtl
        headers['Authorization'] =  "Bearer {}".format(validToken)

        res = requests.get(url, params=params, headers=headers)
        return res

    def on_execute(self, binder, user_id, package, data, *args, **kwargs):
        oauth = self.oauth(binder, user_id, MyInfoPropertyOAuthProvider)
        real_user_id = binder.on_load_state().user_id
        token = OAuthTokenModel.objects.filter(
            component_name=self.oauth_component, user_id=real_user_id
        ).first().get_data()

        uinfin = token["uinfin"]
        res = self.person_request(
            uinfin, token["access_token"], {"CLIENT_ID": self.CLIENT_ID}, {}
        )

        res = res.json()

        output = OutputStatement(user_id)
        if 'code' in res:
            output.append_text("Something went wrong. Please try again later.")
        else:
            user_data = {}
            usable_amount = 0
            percentage = 25
            for field in res:
                user_data[field] = self._normalize(res, field)
            if user_data.get("cpfbalances") and user_data["cpfbalances"] != "unavailable":
                usable_amount = math.ceil(user_data["cpfbalances"]["oa"] / 25)
                output.append_text("Helllo {}! Here is a summary of your current CPF balances.".format(user_data["name"]))
                # balance_text = ""
                balances = {"CPF Balances": {}}
                for balance_type, amount in user_data["cpfbalances"].items():
                    # balance_text += "{}: {}\n".format(balance_type.upper(), amount)
                    balances["CPF Balances"].update({balance_type.upper(): amount})
                # output.append_text(balance_text)
                output.append_node(Expandable(balances))
            if user_data.get("hdbownership") and len(user_data["hdbownership"]) > 0:
                header_text = (
                    "The following property is also in your name:"
                    if len(user_data["hdbownership"]) == 1
                    else "The following properties are also in your name:"
                )
                output.append_text(header_text) 
                for address in user_data["hdbownership"]:
                    user_property = {"Property": {"address": address}}
                    output.append_node(Expandable(user_property))
            output.append_text(
                "You can use up to {}% of your OA balance to finace a {} property. This means you can use up to ${} of your CPF savings"
                .format(percentage, number_to_ordinal(len(user_data["hdbownership"]) + 1), usable_amount)
                )
            output.append_text("I hope this information was helpful! Anything else I can assist with?")
        binder.post_message(output)

    def on_search(binder, user_id, package, data, query, kwargs):
        pass

    def _normalize(self, data, key):
        if key == 'name':
            return data['name']['value']
        elif key == 'hdbownership':
            addresses = []
            if len(data['hdbownership']) > 0:
                for record in data['hdbownership']:
                    address = record["address"]
                    
                    block = address['block']['value']
                    street = address['street']['value']
                    floor = address['floor']['value']
                    unit = address['unit']['value']
                    building = address['building']['value']
                    postal = address['postal']['value']
                    country = address['country']['desc']
                    addresses.append("{} {}, {} {} {}, {} {}".format(block, street, floor, unit, building, country, postal))
            return addresses
        elif key == 'cpfbalances':
            if data['cpfbalances'].get('unavailable') == True:
                return 'unavailable'
            else:
                balances = {}
                if data['cpfbalances'].get("ma"):
                    balances["ma"] = data['cpfbalances']["ma"]["value"]
                if data['cpfbalances'].get("oa"):
                    balances["oa"] = data['cpfbalances']["oa"]["value"]
                if data['cpfbalances'].get("sa"):
                    balances["sa"] = data['cpfbalances']["sa"]["value"]
                if data['cpfbalances'].get("ra"):
                    balances["ra"] = data['cpfbalances']["ra"]["value"]
                return balances
