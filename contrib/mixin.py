from django.apps import apps
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.db import models

def models_list():
    from core.models import Project
    return {
        'user':get_user_model,
        'project':Project,
   }

def env(object, option = 'name_to_model'):
    named_instance = models_list()
    #name_to_model | class_to_model | name_to_class
    if option == 'class_to_model':
        for key,val in named_instance.items():
            if str(val) == str(object):
                return named_instance[key]()
        return False
    if option == 'name_to_class':
        return named_instance[object]
    return named_instance[object]()

def request():
    from django_middleware_global_request.middleware import get_request
    return get_request()

RESTRICT_SUPER_USER = False

class AccessRights:

    def __init__(self):
        self.group_access_rights = {}
        self.user_rights = False

    # Todo [Read,Create,Write,Unlink] : [1,1,1,1]
    def add_group_rights(self, group_name, read, create, write, unlink):
         self.group_access_rights[group_name] = [read, create, write, unlink]

    def has_group_rights(self, group_name,  access_type):
        if group_name in self.group_access_rights:
            if access_type == Access.READ:
                return self.group_access_rights[group_name][0] == 1
            elif access_type == Access.CREATE:
                return self.group_access_rights[group_name][1] == 1
            elif access_type == Access.WRITE:
                return self.group_access_rights[group_name][2] == 1
            elif access_type == Access.UNLINK:
                return self.group_access_rights[group_name][3] == 1
        return False

    # Todo only PrimaryField/IntegerField/Many2One/Many2Many
    def add_user_rights(self, reference_field, read, write, unlink):
        self.user_rights = [reference_field, [read, write, unlink]]

    # Todo only PrimaryField/IntegerField/Many2One/Many2Many allowed $user_id must be non zero int
    def has_user_rights(self, object, user_id, access_type):
        if not self.user_rights:
           return True
        if access_type == Access.READ:
            if self.user_rights[1][0] != 1:
                return False
        elif access_type == Access.WRITE:
            if self.user_rights[1][1] != 1:
                return False
        elif access_type == Access.UNLINK:
            if self.user_rights[1][2] != 1:
                return False

        if hasattr(object, self.user_rights[0]):
            field_object = object._meta.get_field(self.user_rights[0])
            field_type = field_object.get_internal_type()
            field_value = field_object.value_from_object(object)
            if field_type == 'AutoField':
                return field_value == user_id
            elif field_type == 'IntegerField':
                return field_value == user_id
            elif field_type == 'ForeignKey':
                return field_value == user_id
            elif field_type == 'OneToOneField':
                return field_value == user_id
            elif field_type == 'ManyToManyField':
                for single_object in field_value:
                    if single_object.id == user_id:
                        return True

        return False

class Access:
    READ = 'read'
    WRITE = 'write'
    UNLINK = 'unlink'
    CREATE = 'create'

class Model:

    def __init__(self, *args, **kwargs):
        super(Model, self).__init__(*args, **kwargs)
        self.rights = AccessRights()
        self._object = self._model_object()
        self._force_access = False
        self._user_id = False
        self.security(self.rights)

    def _model_object(self):
        app_label = self._meta.app_label
        model_name = self.__class__.__name__
        object = apps.get_model(app_label=app_label, model_name=model_name)
        return object.objects

    def get_fields_value(self, fields):
        return self.serialize(fields)

    def serialize(self, fields = []):
        if 'id' not in fields:
            fields.insert(0, "id")
        values = {}
        for name in fields:
            values[name] = self._get_field_value(name)
        return values


    def _get_field_value(self, name):
        if hasattr(self, name):
            field_object = self._meta.get_field(name)
            field_type = field_object.get_internal_type()
            field_value = field_object.value_from_object(self)
            if field_type  in ['CharField', 'AutoField', 'TextField','EmailField','BooleanField','IntegerField']:
                return field_value
            elif field_type  in ['ForeignKey','OneToOneField']:
                if field_value:
                    if self._force_access:
                       single_value = getattr(self, name)
                    else:
                       single_value = getattr(self, name).get()
                    return [single_value.id, str(single_value)]
            elif field_type  in ['ManyToManyField']:
                ids = []
                for single_value in field_value:
                    if self._force_access:
                        ids.append(single_value.id)
                    else:
                        ids.append(single_value.get().id)
                return ids
        return False

    def security(self, rights):
        pass

    def sudo(self, uid = False):
        self._force_access = True
        self._user_id = uid
        return self

    def check_group_rights(self, access_type):
        if self._force_access:
            return
        user = request().user
        if not user.is_authenticated:
            raise PermissionDenied('public user denied to {} model {}'.format(access_type, self.__class__.__name__))
        elif not user.is_active:
            raise PermissionDenied('inactive user denied to {} model {}'.format(access_type, self.__class__.__name__))
        elif user.is_superuser and not RESTRICT_SUPER_USER:
            return
        for group in user.res_groups.all():
            if self.rights.has_group_rights(group.name, Access.READ):
                return

        raise PermissionDenied('Sorry you are not allowed to {} model {}'.format(access_type, self.__class__.__name__))

    def check_users_rights(self, object,  access_type, raise_exception = True):
        if self._force_access:
            return True
        user = request().user
        if not user.is_authenticated:
            raise PermissionDenied('public user denied to {} model {}'.format(access_type, self.__class__.__name__))
        elif not user.is_active:
            raise PermissionDenied('inactive user denied to {} model {}'.format(access_type, self.__class__.__name__))
        elif user.is_superuser and not RESTRICT_SUPER_USER:
            return True
        if self.rights.has_user_rights(object, user.id, access_type):
            return True
        if not raise_exception:
            return False
        raise PermissionDenied("Sorry you are not allowed to '{}' record '{}({})' with uid({})".format(
                               access_type, self.__class__.__name__, object.id, user.id ))

    def get(self):
        self.check_group_rights(Access.READ)
        self.check_users_rights(self,Access.READ)
        return self


    def read(self, id):
        self.check_group_rights(Access.READ)
        object = self._object.filter(id=id).first()
        if object:
            object._force_access = self._force_access
            object._user_id = self._user_id
            self.check_users_rights(object, Access.READ)
            return object
        return object

    def create(self, values):
        self.check_group_rights(Access.CREATE)
        print(values,'jnbuibui====')
        pre_vals = {}
        for key, val in values.items():
            if hasattr(self, key):
                field_object = self._meta.get_field(key)
                field_type = field_object.get_internal_type()
                if field_type  in ['CharField', 'TextField','EmailField','BooleanField','IntegerField']:
                    pre_vals[key] = val
                elif field_type  in ['ForeignKey','OneToOneField']:
                    rel_object = env(field_object.related_model, option='class_to_model')._model_object()
                    rel = rel_object.get(id=val)
                    pre_vals[key] = rel

        record = self._object.create(**pre_vals)

        for key, val in values.items():
            if hasattr(self, key):
                field_object = self._meta.get_field(key)
                field_type = field_object.get_internal_type()
                if field_type  in ['ManyToManyField']:
                    rel_object = env(field_object.related_model, option='class_to_model')._model_object()
                    for rel in  rel_object.filter(id__in=val):
                        getattr(record, key).add(rel)

        return record


    def write(self, values):
        self.check_group_rights(Access.WRITE)
        self.check_users_rights(self, Access.WRITE)
        for key, val in values.items():
            if hasattr(self, key):
               field_object = self._meta.get_field(key)
               field_type = field_object.get_internal_type()
               if field_type  in ['CharField', 'TextField','EmailField','BooleanField','IntegerField']:
                   setattr(self, key, val)
               elif field_type  in ['ForeignKey','OneToOneField']:
                   rel_object = env(field_object.related_model, option='class_to_model')._model_object()
                   rel = rel_object.get(id=val)
                   setattr(self, key, rel)
               elif field_type  in ['ManyToManyField']:
                   getattr(self, key).clear()
                   rel_object = env(field_object.related_model, option='class_to_model')._model_object()
                   for rel in  rel_object.filter(id__in=val):
                       getattr(self, key).add(rel)
        self.save()
        return True

    def unlink(self):
        self.check_group_rights(Access.UNLINK)
        self.check_users_rights(self, Access.UNLINK)
        self.delete()
        return True

    def search(self, filter = [], limit = 0, offset = 0, sort = ['id', 'desc'], raise_exception=False):
        self.check_group_rights(Access.READ)

        results =  []
        sort = '-'+sort[0] if not sort[1].lower() == 'asc' else sort[0]
        records = self._object.filter(**self._load_filter(filter)).order_by(sort)
        records = records[offset:] if limit == 0 else records[offset:offset+limit]

        for object in records:
            object._force_access = self._force_access
            object._user_id = self._user_id
            if self.check_users_rights(object, Access.READ, raise_exception):
                results.append(object)

        return results


    def search_count(self, filter=[]):
        return len(self.search(filter))

    def name_search(self, query):
        results =  []
        sort = self.name_filter(query)[2]
        limit = self.name_filter(query)[1]
        filter = self.name_filter(query)[0]
        sort = '-'+sort[0] if not sort[1].lower() == 'asc' else sort[0]
        records = self._object.filter(**self._load_filter(filter)).order_by(sort)[:limit]
        for object in records:
            if self.check_users_rights(object, Access.READ, False):
                results.append([object.id, str(object)])
        return results

    def name_filter(self, query):
        if query:
            return [[['name__contains',query]], 5, ['name', 'desc']]
        else:
            return [[], 5, ['name', 'desc']]

    def _load_filter(self, filter):
        conditions = {}
        for con in filter:
            if con[0] not in conditions:
                conditions[con[0]] = con[1]
        return conditions
