# -*- coding: utf-8 -*-

'''

  canteen dispatch
  ~~~~~~~~~~~~~~~~

  WSGI dispatch entrypoint. INCEPTION.

  :author: Sam Gammon <sam@keen.io>
  :copyright: (c) Keen IO, 2013
  :license: This software makes use of the MIT Open Source License.
            A copy of this license is included as ``LICENSE.md`` in
            the root of the project.

'''

app = None


def spawn(app,
        dev,
        config,
        root=None):

  '''  '''

  # canteen core & util
  from canteen.core import runtime
  return runtime.Runtime.spawn(app).configure(config)


def run(app=None,
    root=None,
    interface='127.0.0.1',
    port=8080,
    dev=True,
    config={}):

  '''  '''

  return spawn(app, dev, config, root).serve(interface, port)


def dispatch():

  '''  '''

  pass


__all__ = (
  'spawn',
  'run',
  'dispatch'
)
