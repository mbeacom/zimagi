from django.conf import settings
from django.db import models as django

from systems.command.parsers import python
from systems.models import fields
from utility.data import ensure_list

import os
import sys
import pathlib
import importlib
import imp
import inflect
import copy
import logging
import json
import oyaml


logger = logging.getLogger(__name__)


class ModelNotExistsError(Exception):
    pass

class SpecNotFound(Exception):
    pass


class ModelGenerator(object):

    def __init__(self, key, name, **options):
        self.parser = python.PythonValueParser(None, (settings, django, fields))
        self.pluralizer = inflect.engine()
        self.key = key
        self.name = name
        self.full_spec = settings.MANAGER.index.spec
        self.spec = self.full_spec[key].get(name, None)
        self.app_name = self.spec.get('app', name)
        self.abstract = True

        if key == 'data':
            self.spec = self.spec.get(key, None)
            self.abstract = False

        self.class_name = self.get_model_name(name, self.spec)

        self.ensure_model_files()
        module_info = self.get_module(self.app_name, self.spec)
        self.module = module_info['module']
        self.module_path = module_info['path']

        self.parents = []
        self.attributes = {}
        self.facade_attributes = {}

        self.facade = self.get_facade()


    @property
    def klass(self):
        override_class_name = "{}Override".format(self.class_name)
        klass = None

        if getattr(self.module, override_class_name, None):
            klass = getattr(self.module, override_class_name)
        elif getattr(self.module, self.class_name, None):
            klass = getattr(self.module, self.class_name)

        if klass:
            klass._meta.facade_class = self.facade
        return klass


    def get_facade(self):
        facade_class_name = "{}Facade".format(self.class_name)
        override_class_name = "{}Override".format(facade_class_name)

        if getattr(self.module, override_class_name, None):
            return getattr(self.module, override_class_name)
        elif getattr(self.module, facade_class_name, None):
            return getattr(self.module, facade_class_name)

        return self.create_facade(facade_class_name)


    def get_model_name(self, name, spec = None):
        if spec and 'model' in spec:
            return spec['model']
        return name.title()

    def get_model(self, name, type_function):
        klass = self.parse_values(name)
        if isinstance(klass, str):
            klass = type_function(name)
        return klass

    def get_class_name(self, name, key):
        klass = self.parse_values(name)
        if isinstance(klass, str):
            try:
                spec = self.full_spec[key][klass]
                module = self.get_module(name, spec, key)['module'].__name__

                if key == 'data':
                    module_path = spec.get('app', name)
                    spec = spec['data']
                else:
                    module_path = module.__name__

                model_name = self.get_model_name(klass, spec)
                model_override_name = "{}Override".format(model_name)

                if getattr(module, model_override_name, None):
                    model_name = model_override_name

                return "{}.{}".format(module_path, model_name)

            except Exception as e:
                logger.error(e)

            raise ModelNotExistsError("Base class for key {} does not exist".format(klass))
        return klass.__name__


    def create_module(self, module_path):
        module = imp.new_module(module_path)
        sys.modules[module_path] = module
        return module

    def get_module(self, name, spec, key = None):
        data_spec = self.full_spec['data']

        if key is None:
            key = self.key

        if key == 'data_base':
            module_path = "data.base.{}".format(name)
        elif key == 'data_mixins':
            module_path = "data.mixins.{}".format(name)
        elif key == 'data':
            module_path = "data.{}.models".format(name)
        else:
            raise SpecNotFound("Key {} is not supported for data: {}".format(key, name))

        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError:
            module = self.create_module(module_path)

        return {
            'module': module,
            'path': module_path
        }


    def init(self, **attributes):
        self.init_parents(**attributes)
        self.init_default_attributes(**attributes)
        self.init_fields(**attributes)

    def init_parents(self, **attributes):
        if 'base' not in self.spec:
            from systems.models import base
            self.parents = [ attributes.get('base_model', base.BaseModel) ]
        else:
            self.parents = [ self.get_model(self.spec['base'], BaseModel) ]

        if 'mixins' in self.spec:
            for mixin in ensure_list(self.spec['mixins']):
                self.parents.append(self.get_model(mixin, ModelMixin))

    def init_default_attributes(self, **attributes):
        meta_info = self.parse_values(copy.deepcopy(self.spec.get('meta', {})))

        if self.abstract:
            meta_info['abstract'] = True

        meta_info['verbose_name'] = self.name
        meta_info['verbose_name_plural'] = self.pluralizer.plural(self.name)
        meta_info['facade_class'] = self.get_facade()

        self.attributes = {
            '__module__': self.module_path,
            'Meta': type('Meta',
                (getattr(self.parents[0], 'Meta', object),),
                meta_info
            )
        }

    def init_fields(self, **attributes):

        def get_display_method(field_name, color = None):

            def get_field_display(self, instance, value, short):
                value = json.loads(value)
                if isinstance(value, (dict, list, tuple)):
                    value = oyaml.dump(value, indent = 2).strip()

                if color and value is not None:
                    return getattr(self, "{}_color".format(color))(value)
                return str(value)

            get_field_display.__name__ = "get_field_{}_display".format(field_name)
            return get_field_display

        for field_name, field_info in self.spec.get('fields', {}).items():
            if field_info is None:
                self.attribute(field_name, None)
            else:
                field_class = self.parse_values(field_info['type'])
                field_options = self.parse_values(field_info.get('options', {}))

                if 'relation' in field_info:
                    field_relation_class = self.get_class_name(field_info['relation'], 'data')

                    if 'related_name' not in field_options:
                        field_options['related_name'] = "{}_relation".format(self.name)

                    self.attribute(field_name, field_class(field_relation_class, **field_options))
                    color = field_info.get('color', 'relation')
                else:
                    self.attribute(field_name, field_class(**field_options))
                    color = field_info.get('color', None)

                self.facade_method(get_display_method(field_name, color))

        if 'meta' in self.spec:
            for field_name in self.spec['meta'].get('dynamic_fields', []):
                self.facade_method(get_display_method(field_name, 'dynamic'))


    def attribute(self, name, value):
        self.attributes[name] = value

    def facade_attribute(self, name, value):
        self.facade_attributes[name] = value

    def method(self, method, *spec_fields):
        if self._check_include(spec_fields):
            self.attributes[method.__name__] = method

    def facade_method(self, method, *spec_fields):
        if self._check_include(spec_fields):
            self.facade_attributes[method.__name__] = method

    def _check_include(self, spec_fields):
        include = True
        if spec_fields:
            for field in spec_fields:
                if field not in self.spec:
                    include = False
        return include


    def create(self):
        parent_classes = copy.deepcopy(self.parents)
        parent_classes.reverse()

        model = type(self.class_name, tuple(parent_classes), self.attributes)
        model.__module__ = self.module.__name__
        setattr(self.module, self.class_name, model)
        return model

    def create_facade(self, class_name):
        parent_classes = []

        for parent in reversed(self.parents):
            if getattr(parent, '_meta', None) and getattr(parent._meta, 'facade_class', None):
                parent_classes.append(parent._meta.facade_class)

        if not parent_classes:
            from systems.models import facade
            parent_classes = [ facade.ModelFacade ]

        facade = type(class_name, tuple(parent_classes), self.facade_attributes)
        facade.__module__ = self.module.__name__
        setattr(self.module, class_name, facade)
        return facade


    def ensure_model_files(self):
        if not self.abstract:
            data_info = settings.MANAGER.index.module_map['data'][self.app_name]
            model_dir = os.path.join(data_info.path, 'data', self.app_name)
            migration_dir = os.path.join(model_dir, 'migrations')

            pathlib.Path(migration_dir).mkdir(mode = 0o755, parents = True, exist_ok = True)
            pathlib.Path(os.path.join(model_dir, 'models.py')).touch(mode = 0o644, exist_ok = True)
            pathlib.Path(os.path.join(migration_dir, '__init__.py')).touch(mode = 0o644, exist_ok = True)


    def parse_values(self, item):
        if isinstance(item, (list, tuple)):
            for index, element in enumerate(item):
                item[index] = self.parse_values(element)
        elif isinstance(item, dict):
            for name, element in item.items():
                item[name] = self.parse_values(element)
        elif isinstance(item, str):
            item = self.parser.interpolate(item)

        return item


def BaseModel(name):
    return AbstractModel('data_base', name)

def BaseModelFacade(name):
    model = BaseModel(name)
    return model._meta.facade_class

def ModelMixin(name):
    from systems.models import base
    return AbstractModel('data_mixins', name,
        base_model = base.BaseMixin
    )

def ModelMixinFacade(name):
    mixin = ModelMixin(name)
    return mixin._meta.facade_class


def AbstractModel(key, name, **options):
    model = ModelGenerator(key, name, **options)
    if model.klass:
        return model.klass

    if not model.spec:
        raise ModelNotExistsError("Abstract model {} does not exist yet".format(model.class_name))

    return _create_model(model, options)

def Model(name, **options):
    model = ModelGenerator('data', name, **options)
    if model.klass:
        return model.klass

    if not model.spec:
        raise ModelNotExistsError("Model {} does not exist yet".format(model.class_name))

    return _create_model(model, options)

def ModelFacade(name):
    model = Model(name)
    return model._meta.facade_class


def _create_model(model, options):
    model.init(**options)
    _include_base_methods(model)
    return model.create()

def _include_base_methods(model):

    def __str__(self):
        return "{} <{}>".format(name, model.class_name)

    def get_id(self):
        return getattr(self, model.spec['id'])

    def get_id_fields(self):
        return ensure_list(model.spec.get('id_fields', []))

    def key(self):
        return model.spec['key']

    def _ensure(self, command, reinit = False):
        reinit_original = reinit
        if not reinit:
            for trigger in ensure_list(model.spec['triggers']):
                reinit = command.get_state(trigger, True)
                if reinit:
                    break
        if reinit:
            self.ensure(command, reinit_original)
            for trigger in ensure_list(model.spec['triggers']):
                Model('state').facade.store(trigger, value = False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for trigger in ensure_list(model.spec['triggers']):
            Model('state').facade.store(trigger, value = True)

    def clear(self, **filters):
        result = super().clear(**filters)
        for trigger in ensure_list(model.spec['triggers']):
            Model('state').facade.store(trigger, value = True)
        return result

    def get_packages(self):
        return model.spec['packages']

    model.method(__str__)
    model.method(get_id, 'id')
    model.method(get_id_fields)
    model.method(save, 'triggers')
    model.facade_method(_ensure)
    model.facade_method(clear, 'triggers')
    model.facade_method(key, 'key')
    model.facade_method(get_packages, 'packages')
