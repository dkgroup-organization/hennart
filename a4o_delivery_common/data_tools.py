# This file is part of an Adiczion's Module.
# The COPYRIGHT and LICENSE files at the top level of this repository
# contains the full copyright notices and license terms.
from odoo import _
from datetime import datetime
from operator import attrgetter
from copy import deepcopy
import logging
import json

_logger = logging.getLogger(__name__)


class Struct(object):
    'Data Structure'
    # model = None
    value = None
    defaults = None

    def __init__(self, model, record, credential=None, defaults=None):
        if defaults:
            self.defaults = deepcopy(defaults)
        # We use the model to store its values, so we have to duplicate it !
        self.value = deepcopy(model)
        # self.model = model
        self.credential = credential
        self.value = self._set_value(self.value, record)

    def _set_value(self, model, record):
        'updates the model with the contents of the record'
        if isinstance(model, dict):
            for k, v in model.items():
                model[k] = self._set_value(v, record)
            return model
        elif isinstance(model, list):
            for i, l in enumerate(model):
                model[i] = self._set_value(l, record)
            return model
        elif isinstance(model, List):
            if self.defaults:
                model.defaults = self.defaults
            model.set(record)
            return model.get()
        elif isinstance(model, (Integer, Float, Char)):
            key = getattr(model, 'late_default')
            if key:
                model.default = self.defaults.get(key)
            model.set(record)
            return model.get()
        else:
            return model

    def get(self):
        'Returns the model completed with the data'
        return self.value

    def json(self):
        return json.dumps(self.get())


class Item(object):
    '''Base class of Item

    Attributs:
      name: Used to identify this object when a error occured
      source: name of the 'record' field whose value must be retrieved.
      eval: string to evaluate with the object 'record'
      default: default value
      required: must content a value
      late_default: the default value will be known when the field is used
                    (for example from another object outside the scope).
                    Not compatible with the use of 'default'.
    '''
    _attrs = {}
    _defaults = {
        'name': None,
        'source': None,
        'required': False,
        'help': None,
        'default': None,
        'value': None,
        'eval': None,
        'late_default': False,
    }
    value = None

    def __init__(self, **kwargs):
        keys = kwargs.keys()
        not_defined = set(keys) - set(self._defaults.keys())
        if not_defined:
            raise AttributeError(_("Some attributes doesn't exist: {}!")
                .format(",".join(not_defined)))
        if 'name' not in kwargs.keys():
            raise AttributeError(_("An attribut 'name' is required!"))
        if len(set(['source', 'eval']) - set(kwargs.keys())) != 1:
            raise AttributeError(
                _("A 'source' or 'eval' attribute is required!"))
        if len(set(['default', 'late_default']) - set(kwargs.keys())) == 0:
            raise AttributeError(
                _("unable to have 'default' and 'late_default' attributes "
                    "together!"))
        attrs = {k: v for k, v in kwargs.items() if v is not None}
        self._attrs = attrs or {}

    def __getattr__(self, name):
        """ Access non-slot field attribute. """
        try:
            if name in self._attrs:
                return self._attrs[name]
            return self._defaults[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        '''Set slot or non-slot field attribute.'''
        if not hasattr(self, name) and name not in self._defaults.keys():
            raise AttributeError
        if name in self._defaults.keys():
            if (name == 'value'
                    and self._attrs.get('required')
                    and not bool(value)):
                raise ValueError(_("A value for '{}' is required!").format(
                        self._attrs['name']))
            if self._attrs:
                self._attrs[name] = value
            else:
                # replace EMPTY_DICT
                self._attrs = {name: value}
        else:
            object.__setattr__(self, name, value)

    def _check(self, value_type, expected_type):
        if value_type != expected_type:
            raise ValueError("Expected '{}' (type of value: {}({})".format(
                    expected_type.__name__, value_type, self._attrs['name']))

    def set(self, record):
        if self.eval:
            value = eval(self.eval)
        elif self.source:
            value = attrgetter(self.source)(record)
        else:
            value = None
        self.value = value

    def get(self):
        '''Return the value of the struct filled with record data'''
        return self._attrs['value']


class Char(Item):
    'Char'
    Item._defaults.update({
        'max_size': None,
        'truncate': False,
        })

    def __setattr__(self, name, value):
        if name == 'value':
            value = value or self._attrs.get('default', '')
            self._check(type(value), type('str'))
            max_size = self._attrs.get('max_size')
            if max_size and len(value) > max_size:
                if self._attrs.get('truncate'):
                    value = value[:max_size]
                else:
                    raise ValueError("size value ({}) is longer than maximum "
                        "size ({}) for {}!".format(len(value), max_size,
                            self._attrs['name']))
            if value:
                value = value.strip()
        Item.__setattr__(self, name, value)


class Integer(Item):
    'Int'
    Item._defaults.update({
        'convert': False,
        })

    def __setattr__(self, name, value):
        if name == 'value':
            if self._attrs.get('convert'):
                value = int(value)
            if not isinstance(value, int):
                default = self._attrs.get('default', None)
                if default is None:
                    value = default
            self._check(type(value), type(0))
        Item.__setattr__(self, name, value)


class Float(Item):
    'Float'

    def __setattr__(self, name, value):
        if name == 'value':
            if not isinstance(value, float):
                default = self._attrs.get('default', None)
                if default is None:
                    value = default
            self._check(type(value), type(0.0))
        Item.__setattr__(self, name, value)


class List(Item):
    'List'
    Item._defaults.update({
        'content': None,
        'defaults': None,
        })

    def set(self, record):
        if self.source:
            data = getattr(record, self.source)
        elif self.eval:
            data = eval(self.eval)
        else:
            data = record
        self.value = [
            Struct(self._attrs['content'], d,
                defaults=self._attrs.get('defaults')).get()
            for d in data
            ]
