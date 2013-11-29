# -*- coding: utf-8 -*-

'''

  canteen: model adapters
  ~~~~~~~~~~~~~~~~~~~~~~~

  :author: Sam Gammon <sam@keen.io>
  :copyright: (c) Keen IO, 2013
  :license: This software makes use of the MIT Open Source License.
      A copy of this library is included as ``LICENSE.md`` in
      the root of the project.

'''

# module constants
__version__ = (0, 7)  # module version-string
__doc__ = "Contains modules that adapt apptools models to various storage backends."


# abstract adapters
from . import abstract
from .abstract import Mixin
from .abstract import KeyMixin
from .abstract import ModelMixin
from .abstract import ModelAdapter
from .abstract import IndexedModelAdapter

abstract_adapters = (abstract, ModelAdapter, IndexedModelAdapter)


# adapter modules
from . import inmemory

modules = (inmemory,)


# concrete adapters
from .inmemory import InMemoryAdapter

concrete = (InMemoryAdapter,)


# builtin mixins
from . import core
from .core import DictMixin
from .core import JSONMixin

builtin_mixins = (DictMixin, JSONMixin)


__adapters__ = abstract_adapters + modules + concrete + builtin_mixins
