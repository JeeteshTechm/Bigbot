import json
import stripe
import requests
import re
from main.Component import SkillProvider, state_to_string
from main import Log

def _get_form_keys(url):
    html_data = requests.get(url).text
    data = json.loads( re.search(r'FB_PUBLIC_LOAD_DATA_ = (.*?);', html_data, flags=re.S).group(1) )
    return [str('entry.')+str(item) for item in _get_ids(data)]

def _get_ids(d):
    if isinstance(d, dict):
        for k, v in d.items():
            yield from _get_ids(v)
    elif isinstance(d, list):
        if len(d) == 3 and d[1] is None:
            yield d[0]
        else:
            for v in d:
                yield from _get_ids(v)

class JustCOAdapter(SkillProvider):

    def on_execute(self, binder, user_id, package, data, **kwargs):
        if package == 'demo.justco.coworking.plan':
            return self._just_co_payment(binder, user_id, data, **kwargs)
        elif package == 'demo.justco.coworking.onboarding':
            return self._just_co_onboard(binder, user_id, data, **kwargs)
        elif package == 'demo.ytc.hotel.room':
            return self._ytc_hotel_payment(binder, user_id, data, **kwargs)

    def on_search(self, binder, user_id, package, searchable, query, **kwargs):
        return super(JustCOAdapter, self).on_search( binder, user_id, package, searchable, query, **kwargs)

    def _just_co_payment(self, binder, user_id, data, **kwargs):
        # {'space_type': 'space_1', 'location': 'singapore', 'plan_type': 'plan_1'}
        form_id = '1FAIpQLScwI-Lzm2Nb9H4kWLWw7Q6u2wiNaSxpiT48oqAU4np6xsB-FQ'
        url = 'https://docs.google.com/forms/d/e/{}/formResponse'.format(form_id)
        keys = _get_form_keys(url)
        Log.warning('Keys', keys)
        Log.warning('Data', data)
        form_data = {
            keys[0]: data['space_type'],
            keys[1]: data['location'],
            keys[2]: data['plan_type'],
            keys[3]: data['email'],
            keys[4]: '120 Robinson Road',
        }
        user_agent = {'Referer':'https://docs.google.com/forms/d/e/{}/viewform','User-Agent': "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.52 Safari/537.36".format(form_id)}
        r = requests.post(url, data=form_data, headers=user_agent)
        return True

    def _ytc_hotel_payment(self, binder, user_id, data, **kwargs):
        # {'space_type': 'space_1', 'location': 'singapore', 'plan_type': 'plan_1'}
        form_id = '1FAIpQLScwI-Lzm2Nb9H4kWLWw7Q6u2wiNaSxpiT48oqAU4np6xsB-FQ'
        url = 'https://docs.google.com/forms/d/e/{}/formResponse'.format(form_id)
        keys = _get_form_keys(url)
        Log.warning('Keys', keys)
        Log.warning('Data', data)
        form_data = {
            keys[0]: data['space_type'],
            keys[1]: data['location'],
            keys[2]: data['plan_type'],
            keys[3]: data['email'],
            keys[4]: 'YTC Hotel',
        }
        user_agent = {'Referer':'https://docs.google.com/forms/d/e/{}/viewform','User-Agent': "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.52 Safari/537.36".format(form_id)}
        r = requests.post(url, data=form_data, headers=user_agent)
        return True

    def _just_co_onboard(self, binder, user_id, data, **kwargs):
        return True
