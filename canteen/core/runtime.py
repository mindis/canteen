# -*- coding: utf-8 -*-

'''

  canteen runtime core
  ~~~~~~~~~~~~~~~~~~~~

  platform internals and logic to discover/load/inject.

  :author: Sam Gammon <sam@keen.io>
  :copyright: (c) Keen IO, 2013
  :license: This software makes use of the MIT Open Source License.
            A copy of this license is included as ``LICENSE.md`` in
            the root of the project.

'''

# stdlib
import sys
import abc
import inspect
import importlib

# core API
from .meta import Proxy
from .injection import Bridge


class Runtime(object):

  '''  '''

  routes = None  # compiled route map
  config = None  # application config
  bridge = None  # window into the injection pool
  application = None  # WSGI application callable or delegate

  __owner__, __metaclass__ = "Runtime", Proxy.Component

  @classmethod
  def spawn(cls, app):

    '''  '''

    # if we're running as ``Runtime``, resolve a runtime first
    return (cls.resolve() if cls is Runtime else cls)(app)

  @classmethod
  def resolve(cls):

    '''  '''

    # @TODO(sgammon): figure out how to prioritize/select a runtime
    _default, _preferred = None, []
    for child in cls.iter_children():
      if hasattr(child, '__default__') and child.__default__:
        _default = child
        continue
      _preferred.append(child)

    if _preferred:
      return _preferred[0]  # Werkzeug
    return _default  # WSGIref

  def __init__(self, app):

    '''  '''

    self.application, self.bridge = (
      app,
      Bridge()
    )

  def initialize(self):

    '''  '''

    return

  def configure(self, config):

    '''  '''

    self.config = config
    self.initialize()  # let subclasses initialize
    return self

  def serve(self, interface, port, bind_only=False):

    '''  '''

    server = self.bind(interface, port)

    if bind_only:
      return server

    try:
      server.serve_forever()
    except KeyboardInterrupt as e:
      print "Exiting."
      sys.exit(0)
    except Exception as e:
      print "Exiting."
      sys.exit(1)

  def bind_environ(self, environ):

    '''  '''

    from ..logic import http
    self.routes = http.HTTPSemantics.route_map.bind_to_environ(environ)

    return (
      http.HTTPSemantics,
      http.HTTPSemantics.new_request(environ),
      http.HTTPSemantics.new_response()
    )

  def dispatch(self, environ, start_response):

    '''  '''

    from ..base import handler as base_handler

    # resolve URL via bound routes
    http, request, response = self.bind_environ(environ)

    # match route
    endpoint, arguments = self.routes.match()

    # resolve endpoint
    handler = http.resolve_route(endpoint)

    if not handler:  # `None` for handler means it didn't match
      http.error(404)

    # class-based pages/handlers
    if isinstance(handler, type) and issubclass(handler, base_handler.Handler):

      # initialize handler
      flow = handler(*(
        environ,
        start_response
      ), **{
        'runtime': self,
        'request': request,
        'response': response
      })

      # dispatch time: INCEPTION.
      result = flow(arguments)

      if isinstance(result, tuple):

        status, headers, content_type, content = result

        return response.__class__(content, **{
          'status': status,
          'headers': headers,
          'mimetype': content_type
        })(environ, start_response)

      return result(environ, start_response)  # it's a werkzeug Response

    # delegated class-based handlers (for instance, other WSGI apps)
    elif isinstance(handler, type) or callable(handler):

      # make a neat little shim, containing our runtime
      def _foreign_runtime_bridge(*args, **kwargs):

        '''  '''

        return start_response(*args, **kwargs)

      # attach runtime, arguments and actual start_response to shim
      _foreign_runtime_bridge.runtime = self
      _foreign_runtime_bridge.arguments = arguments
      _foreign_runtime_bridge.start_response = start_response

      # initialize foreign handler with replaced start_response
      return handler(environ, _foreign_runtime_bridge)

    # is it a function, maybe?
    if inspect.isfunction(handler):

      # inject stuff into context
      for prop, val in (
        ('runtime', self),
        ('self', self.bridge),
        ('arguments', arguments),
        ('request', request),
        ('response', response),
        ('environ', environ),
        ('start_response', start_response),
        ('Response', response.__class__)):

        handler.__globals__[prop] = val  # inject all the things

      # call with arguments only
      result = handler(**arguments)
      if isinstance(result, response.__class__):
        return response(environ, start_response)  # it's a Response class - call it to start_response

      # a tuple bound to a URL - static response
      elif isinstance(result, tuple):

        if len(result) == 2:  # it's (status_code, response)
          status, response = result
          start_response(status, [('Content-Type', 'text/html; charset=utf-8')])
          return iter([response])

        if len(result) == 3:  # it's (status_code, headers, response)
          status, headers, response = result

          if isinstance(headers, dict):
            headers = headers.items()
            if 'Content-Type' not in headers:
              headers['Content-Type'] = 'text/html; charset=utf-8'

          start_response(status, headers)
          return iter([response])

      elif isinstance(result, basestring):
        start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
        return iter([result])

    # could be a bound response
    if not callable(handler):
      if isinstance(handler, basestring):

        # it's a static response!
        return iter([handler])

    raise RuntimeError('Unrecognized handler type: "%s".' % type(handler))

  @abc.abstractmethod
  def bind(self, interface, address):

    '''  '''

    raise NotImplementedError

  __call__ = dispatch


class Library(object):

  '''  '''

  name = None  # string name of the library
  strict = False  # whether to hard-fail on ImportError
  package = None  # reference to the actual library package/module
  exception = None  # captured ImportError or AttributeError exception, if any
  supported = None  # boolean flag indicating whether this lib is supported or not

  __owner__, __metaclass__ = "Library", Proxy.Component

  def __init__(self, package, strict=False):

    '''  '''

    if isinstance(package, basestring):
      self.name = package
    elif isinstance(package, type(abc)):
      self.name, self.package, self.supported = package.__name__, package, True
    self.strict = strict

  def load(self, *subpackages):

    '''  '''

    loaded = []
    for package in subpackages:
      loaded.append(importlib.import_module('.'.join((self.name, package))))
    if len(loaded) == 1:
      return loaded[0]  # special case: one package only (return it directly)
    return tuple(loaded)  # otherwise, return a tuple of loaded modules

  def __enter__(self):

    '''  '''

    if not self.package and (self.supported is None):
      try:
        self.package = importlib.import_module(self.name)
      except ImportError as e:
        self.supported, self.exception = False, e
        if self.strict:
          raise
      else:
        self.supported = True
    return (self, self.package)

  def __exit__(self, exception_cls, exception, traceback):

    '''  '''

    if exception and exception_cls is NotImplementedError:
      return True
