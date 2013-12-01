# -*- coding: utf-8 -*-

'''

  canteen injection core
  ~~~~~~~~~~~~~~~~~~~~~~

  tools for dependency injection - essentially, walking the
  structure exposed by classes in :py:mod:`core.meta` to
  combine dependencies into compound classes.

  :author: Sam Gammon <sam@keen.io>
  :copyright: (c) Keen IO, 2013
  :license: This software makes use of the MIT Open Source License.
            A copy of this library is included as ``LICENSE.md`` in
            the root of the project.

'''

# canteen meta
from .meta import Proxy


class Delegate(object):

  ''' '''

  __bridge__ = None  # holds bridge for current class to collapsed component set
  __target__ = None  # holds injection target for this delegate (that we will answer for)

  class __metaclass__(type):

    def __new__(cls, name_or_target, bases=None, properties=None):

      '''  '''

      # if it only comes through with a target, it's a subdelegate
      if bases or properties:
        # it's `Delegate` probably - construct it as normal
        name, target = name_or_target, None
        return type.__new__(cls, name, bases, properties)

      # otherwise, construct with an MRO attribute injection
      name, target = None, name_or_target

      def injection_responder(klass, key):

        '''  '''

        if not klass.__bridge__:
          klass.__bridge__ = Proxy.Component.collapse(klass)
        try:
          return klass.__bridge__[key]
        except KeyError:
          raise AttributeError('Could not resolve attribute \'%s\''
                               ' on item \'%s\'.' % (key, klass))

      # inject properties onto MRO delegate, then construct
      return type.__new__(cls.__class__, 'Delegate', (object,), {
        '__bridge__': None,
        '__getattr__': classmethod(injection_responder),
        '__metaclass__': cls,
        '__repr__': cls.__repr__,
        '__target__': target
      })

    def __repr__(cls):

      '''  '''

      return "<delegate root>" if not cls.__target__ else "<delegate '%s'>" % cls.__target__.__name__

  @classmethod
  def bind(cls, target):

    '''  '''

    # wrap in Delegate class context as well
    return cls.__metaclass__.__new__(cls, target)


class Compound(type):

  '''  '''

  __seen__ = set()
  __delegate__ = None

  def mro(cls):

    '''  '''

    for base in cls.__bases__:
      # check if we've seen any of these bases
      if base not in (object, type) or base in cls.__class__.__seen__:
        break
    else:
      # never seen this before - roll in our delegate
      origin = type.mro(cls)
      delegate = Delegate.bind(cls)
      cls.__class__.__seen__.add(cls)

      return (
        [origin[0]] +
        [i for i in filter(lambda x: x not in (object, type), origin[1:])] +
        [y for y in filter(lambda z: z in (object, type), origin[1:])] +
        [delegate]
      )

    # we have seen this class' bases. register it as seen as well to propagate.
    delegate = Delegate.bind(cls)

    # assign delegate and consider in seen classes
    cls.__class__.__delegate__ = delegate
    cls.__class__.__seen__.add(cls)

    return tuple(
      [cls] +
      [i for i in cls.__bases__] +
      [object] +
      [delegate]
    )
