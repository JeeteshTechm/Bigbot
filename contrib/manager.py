from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from . import mixin

class JsonRPC:

    def __init__(self, user):
        self.user = user
        self.request = mixin

    def response(self, result):
        data = result
        return JsonResponse({"jsonrpc": "2.0", "result":data,"id":None})

    # RPC
    def execute_kw(self, model, method, params, id = None):
        if method == 'read':
            result = self.request.env(model).sudo().read(params[0])
            if result:
                fields = params[1]['fields'] if (len(params) == 2 and 'fields' in params[1]) else []
                return result.serialize(fields)
        elif method == 'search_read':
            result = []
            fields = params[1]['fields'] if (len(params) == 2 and 'fields' in params[1]) else []
            limit = params[1]['limit'] if (len(params) == 2 and 'limit' in params[1]) else 0
            offset = params[1]['offset'] if (len(params) == 2 and 'offset' in params[1]) else 0
            sort = params[1]['sort'] if (len(params) == 2 and 'sort' in params[1]) else ['id', 'desc']
            for item in self.request.env(model).sudo().search(params[0],limit,offset,sort):
                result.append(item.serialize(fields))
            return result
        elif method == 'create':
            record = self.request.env(model).sudo().create(params[0])
            if record:
                return record.id
        elif method == 'write':
            record = self.request.env(model).sudo().read(params[0])
            if record:
                return record.sudo().write(params[1])
        elif method == 'unlink':
            for item in params[0]:
                obj = self.request.env(model).sudo().read(item)
                obj.sudo().unlink()
            return True
        elif method == 'search_count':
            return self.request.env(model).sudo().search_count()
        elif method == 'name_search':
            return self.request.env(model).sudo().name_search(params[0])
        else:
            if not id:
               result = getattr(self.request.env(model,option='name_to_class'),method)(*params)
               return result

        return False

























