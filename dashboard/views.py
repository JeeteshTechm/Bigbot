from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.template import RequestContext
from django.http import HttpResponse,JsonResponse
from django.core.exceptions import SuspiciousOperation
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods
import json
import uuid
import requests
from contrib import utils
from core.models import Project,Preference
import yaml
from core.models import User
from django_middleware_global_request.middleware import get_request

def get_data(request):
    data = {
        'user':request.user,
        'uri':request.META['PATH_INFO'],
    }
    data['notifications'] = [{
        'title':'Hello!',
        'body':'Welcome to big bot portal.',
        'sub_title':'moment ago',
        'href':'#'
    }]
    return data

def logout_view(request, *args, **kwargs):
    if request.user.is_authenticated:
        logout(request.user)
    return redirect('/')

def login_view(request, *args, **kwargs):
    if request.user.is_authenticated:
        return redirect('/dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        if username and password:
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request,user)
                return redirect('/dashboard')
    return render(request, 'auth-login.html',{})

def invoice_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request,'invoices.html',data)


def skill_store(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request,'skill_store.html',data)



def logout_view(request, *args, **kwargs):
    logout(request)
    return redirect('/login')

def dashboard_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request,'dashboard.html',data)

def documentation_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request,'documentation.html',data)

def blank_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    return render(request,'content.html',data)


def tree_view(request, model, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    project = Project.get_project(request.user)
    if not project:
        return HttpResponse(status=403)
    return _render_tree(request, project, data, model)

def _render_tree(request, project,  data, model):
    model_columns = {
        'bot.delegate':[['user_id','Name']],
        'input.pattern':[['string','Body'],['delegate_id','Delegate']],
        'delegate.skill':[['name','Name'],['package','Package']],
        'delegate.intent':[['skill_id','Skill']],
        'delegate.utterance':[['body','Body']],
    }
    model_titles = {
        'bot.delegate':'Delegate',
        'input.pattern':'Input Patterns',
        'delegate.skill':'Delegate Skill',
        'delegate.intent':'Delegate Intent',
        'delegate.utterance':'Utterance',
    }
    fields = []
    for item in model_columns[model]:
        fields.append(item[0])
    filter = []
    data['MODEL_NAME'] = model
    data['tree_title'] = model_titles[model]
    if model == 'bot.delegate':
        filter = [['classification',1]]
    data['TREE_META_JSON'] = json.dumps({
        'uuid':project.api_key,
        'token':project.api_secret,
        'host':project.instance_uri,
        'endpoint':'/jsonrpc/object',
        'filter':filter,
        'limit':50,
        'offset':0,
        'sort':['id', 'desc'],
        'model':model,
        'fields' : fields,
        'heads':  model_columns[model],
    })
    if model == 'delegate.skill':
        return render(request, 'tree_skill_view.html', data)
    return render(request, 'tree.html', data)

def _json_rpc_model_request(project, token, model, method, params = []):
    headers = {'content-type': 'application/json'}
    object = {
        "jsonrpc": "2.0",
        "method": "execute_kw",
        "id": None,
        "params": [
            token['uuid'],
            token['token'],
            model,
            method,
        ]
    }
    object['params'].extend(params)
    url = project.instance_uri + '/jsonrpc/object'
    data = json.dumps(object)
    response = requests.post(url =  url, headers=headers, data = data)
    print('======response=====',response)
    if response.status_code == 200:
        return response.json()['result']
    if response.status_code == 403 or response.status_code == 401:
        ProjectUser.revoke_token(get_request().user,project)
        #return _json_rpc_model_request(project,token,model,method,params)
    print(utils.bg('Error >>>>>>> '+str(response.status_code),160))
    return False


def form_view(request, model, id = None, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    project = Project.get_project(request.user)
    if not project:
        return HttpResponse(status=403)
    token = project.get_token(request.user)
    if not token:
        return HttpResponse(status=403)

    data['FORM_META_JSON'] = json.dumps({
        'uuid':token['uuid'],
        'token':token['token'],
        'host':project.instance_uri,
        'endpoint':'/jsonrpc/object',
    })

    # mimic REST method
    request_method = request.POST.get('action').upper() if request.POST.get('action') else request.method

    if model == 'delegate.utterance':
        return _handle_utterance(request, request_method, data, project, token, model, id, 'add_utterance.html')
    elif model == 'delegate.skill':
        return _handle_skill(request, request_method, data, project, token, model, id, 'add_skill.html')
    elif model == 'delegate.intent':
        return _handle_intent(request, request_method, data, project, token, model, id, 'add_intent.html')
    elif model == 'bot.delegate':
        return _handle_delegate(request, request_method, data, project, token, model, id, 'add_delegate.html')
    elif model == 'input.pattern':
        return _handle_input_pattern(request, request_method, data, project, token, model, id, 'add_input.html')

    return HttpResponse(status=501)

def _handle_utterance(request, request_method, data, project, token, model, id, template):
    browse_fields = ['body']

    if request_method == 'POST':
        values = {
            'body':request.POST.get('body'),
        }
        print(request_method,'body=====',values)

        if id:
            _json_rpc_model_request(project,token,model,'write',[id,values])
        else:
            _json_rpc_model_request(project,token,model,'create',[values])
        return redirect('/console/project/'+model)
    # DELETE record
    elif request_method == 'DELETE':
        _json_rpc_model_request(project,token,model,'unlink',[[id]])
        return redirect('/console/project/'+model)
    data['record'] = _json_rpc_model_request(project,token,model,'read',[id,{'fields':browse_fields}])
    return render(request, template, data)

def _handle_skill(request, request_method, data, project, token, model, id, template):
    browse_fields = ['name','package','input_arch','response_arch','active','provider']
    if request_method == 'POST':
        values = {
            'name':request.POST.get('name'),
            'package':request.POST.get('package'),
            'input_arch':request.POST.get('input_arch'),
            'response_arch':request.POST.get('response_arch'),
        }

        if id:
            _json_rpc_model_request(project,token,model,'write',[id,values])
        else:
            _json_rpc_model_request(project,token,model,'create',[values])
        return redirect('/console/project/'+model)
    # DELETE record
    elif request_method == 'DELETE':
        _json_rpc_model_request(project,token,model,'unlink',[[id]])
        return redirect('/console/project/'+model)
    data['record'] = _json_rpc_model_request(project,token,model,'read',[id,{'fields':browse_fields}])
    return render(request, template, data)

def _handle_input_pattern(request, request_method, data, project, token, model, id, template):
    browse_fields = ['string','delegate_id','response_ids']
    if request_method == 'POST':
        string = request.POST.get('string')
        delegate_id = utils.get_int(request,'delegate_id')
        responses = request.POST.getlist('response')
        _json_rpc_model_request(project,token,'input.pattern','post_values',[string,delegate_id,responses,id])
        return redirect('/console/project/'+model)
    # DELETE records
    elif request_method == 'DELETE':
        res_model = request.POST.get('model')
        res_id = id if res_model == 'input.pattern' else request.POST.get('id')
        _json_rpc_model_request(project,token,res_model,'unlink',[[res_id]])
        if res_model == 'response.phrase':
            return redirect(request.path_info)
        return redirect('/console/project/'+model)
    data['record'] = _json_rpc_model_request(project,token,model,'read',[id,{'fields':browse_fields}])
    data['delegates'] = _json_rpc_model_request(project,token,'delegate.delegate','search_read',[[],{'fields':['user_id']}])
    if data['record'] and data['record']['response_ids']:
       data['record']['response_ids'] = _json_rpc_model_request(project,token,'response.phrase',
                                                             'search_read',[[['id__in', data['record']['response_ids']]],{'fields':['string']}])
    return render(request, template, data)

def _handle_delegate(request, request_method, data, project, token, model, id, template):
    browse_fields = ['confidence','default_response','skill_ids','user_id']
    if request_method == 'POST':
        skill_ids = utils.get_int_arr(request, 'delegate_skill')
        confidence = utils.get_int(request, 'confidence')
        user_id = utils.get_int(request, 'partner_id')
        default_response = utils.get_string(request, 'default_response')
        _json_rpc_model_request(project,token,model,'post_values',[user_id, confidence, default_response, skill_ids, id])
        return redirect('/console/project/'+model)
    # DELETE record
    elif request_method == 'DELETE':
        _json_rpc_model_request(project,token,model,'unlink',[[id]])
        return redirect('/console/project/'+model)
    data['record'] = _json_rpc_model_request(project,token,model,'read',[id,{'fields':browse_fields}])
    data['partner_ids'] = _json_rpc_model_request(project,token,'bot.delegate','get_users',[])
    if data['record'] and data['record']['skill_ids']:
        data['skill_ids'] = _json_rpc_model_request(project,token,'delegate.skill',
                             'search_read',[[['id__in', data['record']['skill_ids']]],{'fields':['name']}])
    return render(request, template, data)



def credential_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    # START
    data = get_data(request)
    project = Project.get_project(request.user)
    if not project:
        return HttpResponse(status=403)
    token = project.get_token(request.user)
    if not token:
        return HttpResponse(status=403)
    # END
    if request.method == 'PUT':
        cred = _json_rpc_model_request(project,token,'api.keys','find_api_keys',[token['uuid'],token['token'],True])
        return HttpResponse(status=200)
    data['object'] = _json_rpc_model_request(project,token,'api.keys','find_api_keys',[token['uuid'],token['token']])
    return render(request,'credential.html',data)


def drop_corpus_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    # START
    data = get_data(request)
    project = Project.get_project(request.user)
    if not project:
        return HttpResponse(status=403)
    token = project.get_token(request.user)
    if not token:
        return HttpResponse(status=403)
    # END
    if request.method == 'POST':
        file = request.FILES['file']
        filename = file.name
        if filename.endswith('.yml'):
            corpus_data = yaml.load(file)
            categories = corpus_data['categories']
            conversations = corpus_data['conversations']
            delegate = utils.get_int(request,'delegate')
            for record in conversations:
                res_1 = record[0]
                res_2 = record[1:]
                #print('======',res_1,res_2)
                _json_rpc_model_request(project,token,'input.pattern','post_values',[res_1,delegate,res_2,None])

    data['delegates'] = _json_rpc_model_request(project,token,'bot.delegate','search_read',[[],{'fields':['user_id']}])
    return render(request,'drop.html',data)



def _handle_intent(request, request_method, data, project, token, model, id, template):
    browse_fields = ['skill_id','name']
    if request_method == 'POST':
        print(request.POST)
        name = request.POST.get('name','')
        skill_id = utils.get_int(request,'skill')
        utterance_ids = utils.get_int_arr(request,'utterance')
        print(skill_id,utterance_ids,name,'========')
        _json_rpc_model_request(project,token,model,'post_values',[name,skill_id,utterance_ids,id])
        return redirect('/console/project/'+model)
    # DELETE record
    elif request_method == 'DELETE':
        _json_rpc_model_request(project,token,model,'unlink',[[id]])
        return redirect('/console/project/'+model)
    data['record'] = _json_rpc_model_request(project,token,model,'read',[id,{'fields':browse_fields}])
    data['skill_ids'] = _json_rpc_model_request(project,token,'delegate.skill','search_read',[[],{'fields':['name','package']}])
    data['utterance_ids'] = []
    if id:
        data['utterance_ids'] = _json_rpc_model_request(project,token,'delegate.utterance',
                                                        'search_read',[[['intent_id',id]],{'fields':['body','intent_id']}])

    print(data['record'],'sss')
    return render(request, template, data)



def list_trainer_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    # START
    data = get_data(request)
    project = Project.get_project(request.user)
    if not project:
        return HttpResponse(status=403)
    token = project.get_token(request.user)
    if not token:
        return HttpResponse(status=403)
    # END
    if request.method == 'POST' and request.POST.get('action') == 'delete':
        _json_rpc_model_request(project,token,'input.pattern','delete_list_values',[])
        return redirect('/list-trainer')
    elif request.method == 'POST':
        data_list = request.POST.getlist('data_list')
        if data_list:
            _json_rpc_model_request(project,token,'input.pattern','post_list_values',[data_list])
            return redirect('/list-trainer')
    return render(request,'list_trainer.html',data)


def import_skill(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    # START
    data = get_data(request)
    project = Project.get_project(request.user)
    if not project:
        return HttpResponse(status=403)
    token = project.get_token(request.user)
    if not token:
        return HttpResponse(status=403)
    # END
    file = request.FILES['file']
    filename = file.name
    if filename.endswith('.json'):
        j_data = json.load(file)
        name = j_data['name']
        package = j_data['package']
        provider =  j_data['provider']
        input_arch = json.dumps(j_data['input_arch'])
        response_arch = json.dumps(j_data['response_arch'])
        _json_rpc_model_request(project,token,'delegate.skill','post_values',
                                [name,package,input_arch,response_arch,provider])
    return HttpResponse('OK')

def server_info(request, *args, **kwargs):
    data = requests.get('https://staging-customer-test-01.igotbot.com/stack/info').json()
    return JsonResponse(data)

def settings_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    # START
    data = get_data(request)
    project = Project.get_project(request.user)
    if not project:
        return HttpResponse(status=403)
    token = project.get_token(request.user)
    if not token:
        return HttpResponse(status=403)
    # END
    if request.method == 'POST':
        values = {
            'adapters':json.loads(request.POST.get('body')),
            'themeColor':request.POST.get('themeColor'),
            'skill_cancel_hidden':request.POST.get('skill_cancel').split(','),
            'vueradio':request.POST.get('vueradio'),
            'comp_funct':request.POST.get('comp_funct'),
            'aws_access_id':request.POST.get('aws_access_id'),
            'aws_secret_key':request.POST.get('aws_secret_key'),
            'google_tts_cred':request.POST.get('google_tts_cred'),
            'sendgrid_apikey':request.POST.get('sendgrid_apikey'),
        }
        _json_rpc_model_request(project,token,'preference','post_bundle_values',[values])
        return redirect(request.path_info)
    pref = _json_rpc_model_request(project,token,'preference','get_bundle_values',[token['uuid'],token['token']])
    data.update(pref)
    return render(request,'settings.html',data)

# Tree
def console_tree_view(request, model, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    # START
    data = get_data(request)
    model_columns = {
        'project':[['name','Name'],['customer_id','Customer'],['instance_uri','Host URI'],],
    }
    model_titles = {
        'project':'Project',
    }
    data['MODEL_NAME'] = model
    data['tree_title'] = model_titles[model]
    filter=[]
    fields = []
    for item in model_columns[model]:
        fields.append(item[0])
    data['TREE_META_JSON'] = json.dumps({
        'uuid':False,
        'token':False,
        'host':'',
        'endpoint':'/jsonrpc/object',
        'filter':filter,
        'limit':50,
        'offset':0,
        'sort':['id', 'desc'],
        'model':model,
        'fields' : fields,
        'heads':  model_columns[model],
    })
    return render(request, 'tree_ext.html', data)

@csrf_exempt
def console_from_view(request, model, id = None, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    # START
    data = get_data(request)
    if model == 'project':
        return _handle_project_view(request, request.user, data, id)
    return HttpResponse(status=400)

def _handle_project_view(request, user, data, id):
    if request.method == 'POST':
        name = request.POST.get('name')
        instance_uri = request.POST.get('instance_uri')
        customer_id = User.objects.get(id=utils.get_int(request,'customer_id'))
        if id:
            record = Project.objects.get(id=id)
            record.name = name
            record.customer_id = customer_id
            record.instance_uri = instance_uri
            record.save()
        else:
            record = Project.objects.create(name=name, customer_id=customer_id, instance_uri=instance_uri)
        return redirect('/console/stack/project/{}/'.format(record.id))
    elif request.method == 'DELETE':
        Project.objects.get(id=id).delete()
        return HttpResponse(status=200)
    if id:
       data['record'] = Project.objects.get(id=id)
    data['users'] = User.objects.filter(is_customer=True)
    return render(request,'add_stack.html',data)


def admin_config_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    if request.method == 'POST':
        Preference.put_value('SENDGRID_APIKEY', request.POST.get('SENDGRID_APIKEY'))
        return redirect(request.get_full_path())

    data['SENDGRID_APIKEY'] = Preference.get_value('SENDGRID_APIKEY',None)
    return render(request,'admin_config.html',data)



def mail_test(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/login')
    data = get_data(request)
    data['HOST'] = "http://"+request.META['HTTP_HOST']
    return render(request,'mail-content.html',data)
