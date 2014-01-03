# -*- coding: utf-8 -*-

'''

  canteen: RPC
  ~~~~~~~~~~~~

  :author: Sam Gammon <sam@keen.io>
  :copyright: (c) Keen IO, 2013
  :license: This software makes use of the MIT Open Source License.
            A copy of this license is included as ``LICENSE.md`` in
            the root of the project.

'''

# canteen
from canteen import core
from canteen import base
from canteen import model

# canteen core
from canteen.core import injection

# canteen HTTP
from canteen.logic import http

# canteen util
from canteen.util import decorators
from canteen.util import struct as datastructures

# RPC submodules
from .protocol import *


with core.Library('protorpc', strict=True) as (protorpc, library):

  #### ==== Dependencies ==== ####

  # remote / message packages
  from protorpc import remote as premote
  from protorpc import registry as pregistry
  from protorpc.remote import method as proto_method
  from protorpc.remote import Service as ProtoService

  # message packages
  from protorpc import messages as pmessages
  from protorpc.messages import Field as ProtoField
  from protorpc.messages import Message as ProtoMessage

  # message types
  from protorpc import message_types as pmessage_types
  from protorpc.message_types import VoidMessage as ProtoVoidMessage

  # WSGI internals
  from protorpc import wsgi as pwsgi
  from protorpc.wsgi import util as pwsgi_util
  from protorpc.wsgi import service as pservice


  #### ==== Message Fields ==== ####

  ## VariantField - a hack that allows a fully-variant field in ProtoRPC message classes.
  class VariantField(ProtoField):

      ''' Field definition for a completely variant field. '''

      VARIANTS = frozenset([pmessages.Variant.DOUBLE, pmessages.Variant.FLOAT, pmessages.Variant.BOOL,
                            pmessages.Variant.INT64, pmessages.Variant.UINT64, pmessages.Variant.SINT64,
                            pmessages.Variant.INT32, pmessages.Variant.UINT32, pmessages.Variant.SINT32,
                            pmessages.Variant.STRING, pmessages.Variant.MESSAGE, pmessages.Variant.BYTES, pmessages.Variant.ENUM])

      DEFAULT_VARIANT = pmessages.Variant.STRING

      type = (int, long, bool, basestring, dict, pmessages.Message)


  #### ==== Message Classes ==== ####

  ## Key - valid as a request or a response, specifies an apptools model key.
  class Key(ProtoMessage):

      ''' Message for a :py:class:`apptools.model.Key`. '''

      encoded = pmessages.StringField(1)  # encoded (`urlsafe`) key
      kind = pmessages.StringField(2)  # kind name for key
      id = pmessages.StringField(3)  # integer or string ID for key
      namespace = pmessages.StringField(4)  # string namespace for key
      parent = pmessages.MessageField('Key', 5)  # recursive key message for parent


  ## Echo - valid as a request as a response, simply defaults to 'Hello, world!'. Mainly for testing.
  class Echo(ProtoMessage):

      ''' I am rubber and you are glue... '''

      message = pmessages.StringField(1, default='Hello, world!')


  ## expose message classes alias
  messages = datastructures.WritableObjectProxy(**{

      # apptools-provided messages
      'Key': Key,  # message class for an apptools model key
      'Echo': Echo,  # echo message defaulting to `hello, world` for testing

      # builtin messages
      'Message': ProtoMessage,  # top-level protorpc message class
      'VoidMessage': ProtoVoidMessage,  # top-level protorpc void message

      # specific types
      'Enum': pmessages.Enum,  # enum descriptor / definition class
      'Field': pmessages.Field,  # top-level protorpc field class
      'FieldList': pmessages.FieldList,  # top-level protorpc field list class

      # field types
      'VariantField': VariantField,  # generic hold-anything property (may cause serializer problems - be careful)
      'BooleanField': pmessages.BooleanField,  # boolean true/false field
      'BytesField': pmessages.BytesField,  # low-level binary-safe string field
      'EnumField': pmessages.EnumField,  # field for referencing an :py:class:`pmessages.Enum` class
      'FloatField': pmessages.FloatField,  # field for a floating point number
      'IntegerField': pmessages.IntegerField,  # field for an integer
      'MessageField': pmessages.MessageField,  # field for a sub-message (:py:class:`pmessages.Message`)
      'StringField': pmessages.StringField,  # field for unicode or ASCII strings
      'DateTimeField': pmessage_types.DateTimeField  # field for containing datetime types

  })


  def service_mappings(services, registry_path='/_rpc/meta', protocols=None):

    '''  '''

    import pdb; pdb.set_trace()

    if not protocols:
      from canteen.base import protocol
      protocols = protocol.Protocol.mapping

    if isinstance(services, dict):
      services = services.iteritems()

    final_mapping, paths, registry_map = (
      [],
      set(),
      {} if registry_path else None
    )

    for service_path, service_factory in services:
      service_class = service_factory.service_class if hasattr(service_factory, 'service_class') else service_factory

      if service_path not in paths:
        paths.add(service_path)
      else:
        raise premote.ServiceConfigurationError(
          'Path %r is already defined in service mapping' %
          service_path.encode('utf-8'))

      if registry_map is not None: registry_map[service_path] = service_class
      final_mapping.append(pservice.service_mapping(service_factory, service_path, protocols=protocols))

    if registry_map is not None:
      final_mapping.append(pservice.service_mapping(
        pregistry.RegistryService.new_factory(registry_map), registry_path, protocols=protocols))

    return pwsgi_util.first_found(final_mapping)


  @http.url('rpc', r'/_rpc/v1/<string:service>.<string:method>')
  class ServiceHandler(base.Handler):

    '''  '''

    __services__ = {}  # holds services mapped to their names

    @classmethod
    def add_service(cls, name, service, **config):

      '''  '''

      cls.__services__[name] = (service, config)
      return service

    @decorators.classproperty
    def get_service(cls, name):

      '''  '''

      if name in cls.__services__:
        return cls.__services__[name]

    @decorators.classproperty
    def services(cls):

      '''  '''

      for name, service in cls.__services__.iteritems():
        yield name, service

    @decorators.classproperty
    def application(cls):

      '''  '''

      _services = []
      for name, service in cls.services:
        service, config = service
        _services.append((r'/_rpc/v1/%s' % name, service.new_factory(config=config)))

      return service_mappings(_services, registry_path='/_rpc/meta/registry')

    def OPTIONS(self, service, method):

      '''  '''

      return self.response('GET, HEAD, OPTIONS, PUT, POST')

    def POST(self, service, method):

      '''  '''

      _status, _headers = None, None
      def _respond(status, headers):

        '''  '''

        _status = status
        _headers = headers

      # delegate to service application
      return self.response(self.application(self.environment, _respond), **{
        'status': _status,
        'headers': _headers
      })

    GET = POST


  class Service(premote.Service):

    '''  '''

    __config__ = None  # local configuration
    __bridge__ = None  # dependency injection bridge

    def __init__(self, config=None):

      '''  '''

      self.__bridge__, self.__config__ = (
        injection.Bridge(),
        config
      )

    @property
    def config(self):

      '''  '''

      return self.__config__

    @property
    def platform(self):

      '''  '''

      return self.__bridge__


  class remote(object):

    '''  '''

    name = None  # string name for target
    config = None  # config items for target

    def __init__(self, name, expose='public', **config):

      '''  '''

      if expose != 'public':
        raise NotImplementedError('Private remote methods are not yet implemented.')

      self.name, self.config = name, config

    @classmethod
    def public(cls, name_or_message, response=None, **config):

      '''  '''

      if isinstance(name_or_message, basestring):
        name, request = name_or_message, None
      else:
        name, request = None, name_or_message

      if not name:

        if isinstance(request, type) and issubclass(request, model.Model):
          request_klass = response_klass = request.to_message_model()

        if response and response != request:
          if isinstance(response, type) and issubclass(response, model.Model):
            response_klass = response.to_message_model()

        def _remote_method_responder(method):

          '''  '''

          def _respond(self, request):

            ''' '''

            result = method(self, request)

            if isinstance(result, model.Model):
              return result.to_message()
            return result

          return premote.method(request_klass, response_klass)(_respond)

        return _remote_method_responder
      return cls(name, expose='public', **config)

    @classmethod
    def private(cls, name, **config):

      '''  '''

      return cls(name, expose='private', **config)

    def __call__(self, target):

      '''  '''

      # finally, register the service (if it's a service class)
      if isinstance(target, type) and issubclass(target, Service):
        ServiceHandler.add_service(self.name, target, **self.config)

      return target

  __all__ = (
    'Service',
    'remote',
    'ServiceHandler',
    'service_mappings',
    'messages',
    'Key',
    'Echo',
    'VariantField',
    'protocol'
  )
