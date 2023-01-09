import json
import abc
import os
import importlib.util
import base64
import urllib.parse as urlparse
from urllib.parse import urlencode
from django.template import Context, Template
from django.contrib.auth import get_user_model

class DataLoader:

    def __init__(self, source):
        self.source = source
        self.data = None
        self.type = None

    def from_file(self, reference):
        file_location = "{}/{}".format(self.source.location, reference)
        self.data = open(file_location, 'r').read()
        return self

    def serialize(self):
        from xmljson import badgerfish as bf
        from xmljson import parker, Parker
        from xml.etree.ElementTree import fromstring
        from json import dumps

        data_dict = bf.data(fromstring(self.data))
        if "properties" in data_dict and "attr" in data_dict["properties"]:
            txt = dumps(bf.data(fromstring(self.data))["properties"]["attr"])
            txt = txt.replace("@", "")
            return json.loads(txt)

        return []

class BaseBuilderBlock:

    def __init__(self, source, descriptor):
        self.source = source
        self.component = self.__class__.__module__+'.'+self.__class__.__name__
        self.descriptor = descriptor

    def get_template(self):
        descriptor = self.descriptor.serialize()
        properties = self.load_template(DataLoader(self.source)).serialize()
        connections = self.load_connections()
        return {
            'component':self.component,
            'descriptor':descriptor,
            'template':properties,
            'connections':connections,
        }

    def get_connections(self, properties = []):
        return self.load_connections(properties)

    @abc.abstractmethod
    def load_template(self, loader):
        pass

    @abc.abstractmethod
    def load_connections(self, properties = []):
        # first on is key and second one is display
        return [[-1, ""]]

class Descriptor:

    def __init__(self, name, *args, **kwargs):
        self.name = name

    def serialize(self):
        return self.__dict__

class AppConfig(abc.ABC):

    def __init__(self, source, *args, **kwargs):
        self.source = source
        self.components = []
        self.init(source)

    @abc.abstractmethod
    def init(self, source):
        self.registry()

    @abc.abstractmethod
    def registry(self):
        pass

    def register(self, object):
        self.components.append(object)

class AppSource:

    def __init__(self, name, location, *args, **kwargs):
        self.name = name
        self.location = location
        self.manifest = kwargs.get('manifest')
        self.init = kwargs.get('init')
        self.data = kwargs.get('data')

    def get_application(self):
        return load_instance(self.init).Application(self)

    def get_manifest(self):
        return json.loads(open(self.manifest,'r').read())

    def get_data(self):
        return json.loads(open(self.data,'r').read())

def get_component(instance_class, component = None):
    if component:
        for source in get_apps_sources():
            app = source.get_application()
            for item in app.components:
                if isinstance(item, instance_class):
                    if item.component == component:
                        return item
    else:
        all = []
        for source in get_apps_sources():
            app = source.get_application()
            for item in app.components:
                if isinstance(item, instance_class):
                    all.append(item)
        return all

def get_apps_sources():
    cwd = os.path.abspath(os.getcwd())
    directory = 'apps'
    path = os.path.join(cwd,directory)
    apps = []
    for file in os.listdir(path):
        if not file.startswith('.'):
            app_dir = os.path.join(cwd,directory,file)
            if os.path.isdir(app_dir):
                manifest = os.path.join(cwd,directory,file,'manifest.json')
                init = os.path.join(cwd,directory,file,'init.py')
                data = os.path.join(cwd,directory,file,'data.json')
                location = os.path.join(cwd,directory,file)
                if os.path.exists(manifest) and os.path.exists(init) and os.path.exists(data):
                    apps.append(AppSource(file, location,manifest=manifest, init=init,data=data))
    return apps

def load_instance(location):
    spec = importlib.util.spec_from_file_location("module.init", location)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj
