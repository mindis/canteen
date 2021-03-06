# -*- coding: utf-8 -*-

'''

  canteen HTTP etag-related logic
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  :author: Sam Gammon <sam@keen.io>
  :copyright: (c) Keen IO, 2013
  :license: This software makes use of the MIT Open Source License.
            A copy of this license is included as ``LICENSE.md`` in
            the root of the project.

'''

# core runtime
from canteen.base import logic
from canteen.core import runtime

# canteen utils
from canteen.util import config
from canteen.util import decorators

# core session API
from canteen.core.api.session import SessionEngine
from canteen.core.api.content import ContentFilter


with runtime.Library('werkzeug', strict=True) as (library, werkzeug):


  @decorators.bind('etags')
  class ETags(logic.Logic):

    '''  '''

    @SessionEngine.configure('etags')
    class ETagSessions(SessionEngine):

      '''  '''

      ## == Session Management == ##
      def load(self, context):

        '''  '''

        pass

      def commit(self, context, session):

        '''  '''

        pass

    ## == Configuration == ##
    @decorators.classproperty
    def config(cls):

      '''  '''

      return config.Config().get('http', {}).get('etags', {'debug': True})

    ## == Non-session Management == ##
    @ContentFilter(request=True)
    def request(self, **context):

      '''  '''

      pass

    @ContentFilter(response=True)
    def response(self, **context):

      '''  '''

      pass


  __all__ = (
    'Etags',
  )
