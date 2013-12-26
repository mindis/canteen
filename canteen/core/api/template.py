# -*- coding: utf-8 -*-

'''

  canteen: core template API
  ~~~~~~~~~~~~~~~~~~~~~~~~~~

  exposes a core API for interfacing with template engines
  like :py:mod:`Jinja2`.

  :author: Sam Gammon <sam@keen.io>
  :copyright: (c) Keen IO, 2013
  :license: This software makes use of the MIT Open Source License.
            A copy of this library is included as ``LICENSE.md`` in
            the root of the project.

'''

# stdlib
import os, sys, importlib, time

# core API & util
from . import CoreAPI
from .. import runtime
from .cache import CacheAPI
from canteen.util import decorators


with runtime.Library('jinja2') as (library, jinja2):


  class TemplateLoader(object):

    '''  '''

    pass


  class ModuleLoader(TemplateLoader, jinja2.ModuleLoader):

    '''  '''

    cache = None  # cache of modules loaded
    module = None  # main module
    has_source_access = False  # from jinja's internals

    def __init__(self, module='templates'):

      '''  '''

      try:
        module = importlib.import_module(module)
      except ImportError:
        pass
      self.cache, self.module = CacheAPI.spawn('tpl_%s' % module), module

    def load(self, environment, filename, globals=None):

      '''  '''

      if globals is None:
        globals = {}

      if isinstance(self.module, basestring):
        self.module = importlib.import_module(self.module)

      # Strip '/' and remove extension.
      filename, ext = os.path.splitext(filename.strip('/'))

      t = self.cache.get(filename)
      if not t:
        # Store module to avoid unnecessary repeated imports.
        mod = self.get_module(environment, filename)

        # initialize module
        root, blocks, debug_info = mod.run(environment)

        # manufacture new template object from cached module
        t = object.__new__(environment.template_class)
        t.environment, t.globals, t.name, t.filename, t.blocks, t.root_render_func, t._module, t._debug_info, t._uptodate = (
          environment,
          globals,
          mod.name,
          filename,
          blocks,
          root,
          None,
          debug_info,
          lambda: True
        )

        self.cache.set(filename, t)
      return t

    def get_module(self, environment, template):

      ''' Converts a template path to a package path and attempts import, or else raises Jinja2's TemplateNotFound. '''

      import jinja2

      # Convert the path to a module name.
      prefix, obj = (self.module.__name__ + '.' + template.replace('/', '.')).rsplit('.', 1)
      prefix, obj = str(prefix), str(obj)

      try:
        return getattr(__import__(prefix, None, None, [obj]), obj)
      except (ImportError, AttributeError):
        raise jinja2.TemplateNotFound(template)


  class FileLoader(TemplateLoader, jinja2.FileSystemLoader):

    '''  '''

    has_source_access = True


  class ExtensionLoader(ModuleLoader):

    '''  '''

    pass


@decorators.bind('template', namespace=False)
class TemplateAPI(CoreAPI):

  '''  '''

  with runtime.Library('jinja2') as (library, jinja2):

    '''  '''

    # default syntax support method
    def syntax(self, handler, environment, config):

      '''  '''

      return environment

    # is there HAML syntax support?
    with runtime.Library('hamlish_jinja') as (haml_library, haml):

      '''  '''

      def syntax(self, handler, environment, config):

        '''  '''

        if config.debug:
          environment.hamlish_mode = 'indented'
          environment.hamlish_debug = True

        # apply config overrides
        if 'haml' in config.config:

          for (config_item, target_attr) in (
            ('mode', 'hamlish_mode'),
            ('extensions', 'hamlish_file_extensions'),
            ('div_shortcut', 'hamlish_enable_div_shortcut')):

            if config_item in config.config['haml']:
              setattr(environment, target_attr, config.config['haml'][config_item])

        return environment

    @property
    def engine(self):

      '''  '''

      return jinja2

    def environment(self, handler, config):

      '''  '''

      # grab template path, if any
      output = config.get('TemplateAPI', {'debug': True})
      path = config.app.get('paths', {}).get('templates', 'templates/')
      jinja2_cfg = output.get('jinja2', {
        'autoescape': True,
        'optimized': True,
        'extensions': (
            'jinja2.ext.autoescape',
            'jinja2.ext.with_',
        )
      })

      # shim-in our loader system, unless it is overriden in config
      if 'loader' not in jinja2_cfg:
        if (output.get('force_compiled', False)) or (isinstance(path, dict) and 'compiled' in path and (not __debug__)):
          jinja2_cfg['loader'] = ModuleLoader(path['compiled'])  # @TODO(sgammon): fix this hard-coded value
        else:
          if isinstance(path, dict) and 'source' not in path:
            raise RuntimeError('No configured template source path.')
          jinja2_cfg['loader'] = FileLoader(path['source'] if isinstance(path, dict) else path)

      # make our new environment
      j2env = self.syntax(handler, self.engine.Environment(**jinja2_cfg), config)

      # allow jinja2 syntax overrides
      if 'syntax' in output:
        for override, directive in filter(lambda x: x[0] in output['syntax'], (
          ('block', ('block_start_string', 'block_end_string')),
          ('comment', ('comment_start_string', 'comment_end_string')),
          ('variable', ('variable_start_string', 'variable_end_string')))):

          # zip and properly set each group
          for group in zip(directive, output['syntax'][override]):
            setattr(j2env, *group)

      return j2env

  @decorators.bind('template.base_headers', wrap=property)
  def base_headers(self):

    '''  '''

    import canteen

    return filter(lambda x: x and x[1], [

      ('Cache-Control', 'no-cache; no-store'),
      ('X-UA-Compatible', 'IE=edge,chrome=1'),
      ('X-Debug', '1' if canteen.debug else '0'),
      ('Vary', 'Accept,Cookie'),
      ('Server', 'canteen/%s Python/%s' % (
        '.'.join(map(unicode, canteen.__version__)),
        '.'.join(map(unicode, (
          sys.version_info.major,
          sys.version_info.minor,
          sys.version_info.micro
        )))
      )) if __debug__ else ('Server', 'Canteen/Python')

    ])

  @decorators.bind('template.base_context')
  def base_context(self):

    '''  '''

    return {

      # Python Builtins
      'all': all, 'any': any,
      'int': int, 'str': str,
      'len': len, 'map': map,
      'max': max, 'min': min,
      'enumerate': enumerate,
      'zip': zip, 'bool': bool,
      'list': list, 'dict': dict,
      'tuple': tuple, 'range': range,
      'round': round, 'slice': slice,
      'xrange': xrange, 'filter': filter,
      'reduce': reduce, 'sorted': sorted,
      'unicode': unicode, 'reversed': reversed,
      'isinstance': isinstance, 'issubclass': issubclass

    }

  @decorators.bind('template.render')
  def render(self, handler, config, template, context, _direct=False):

    '''  '''

    # render template & return content iterator
    start = time.clock()
    content = self.environment(handler, config).get_template(template).render(**context)
    end = time.clock()

    total = end - start
    print "Rendered \"%s\" in %sms." % (template, str(round(total * 1000, 2)))

    if _direct:
      return content

    return iter([content])
