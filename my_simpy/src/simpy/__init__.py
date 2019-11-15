"""
The ``simpy`` module aggregates SimPy's most used components into a single
namespace. This is purely for convenience. You can of course also access
everything (and more!) via their actual submodules.

The following tables list all of the available components in this module.

{toc}

"""
from pkgutil import extend_path

from .core import Environment
from .rt import RealtimeEnvironment
from .exceptions import SimPyException, Interrupt, StopProcess
from .events import Event, Timeout, Process, AllOf, AnyOf
from .resources.resource import (
    Resource, PriorityResource, PreemptiveResource,FiniteQueueResource)
from .resources.container import Container
from .resources.store import (
    Store, PriorityItem, PriorityStore, FilterStore)


def compile_toc(entries, section_marker='='):
    """Compiles a list of sections with objects into sphinx formatted
    autosummary directives."""
    toc = ''
    for section, objs in entries:
        toc += '\n\n%s\n%s\n\n' % (section, section_marker * len(section))
        toc += '.. autosummary::\n\n'
        for obj in objs:
            toc += '    ~%s.%s\n' % (obj.__module__, obj.__name__)
    return toc


toc = (
    ('Environments', (
        Environment, RealtimeEnvironment,
    )),
    ('Events', (
        Event, Timeout, Process, AllOf, AnyOf, Interrupt,
    )),
    ('Resources', (
        Resource, PriorityResource, PreemptiveResource, Container, Store,
        PriorityItem, PriorityStore, FilterStore,
    )),
    ('Exceptions', (
        SimPyException, Interrupt, StopProcess,
    )),
)

# Use the toc to keep the documentation and the implementation in sync.
if __doc__:
    __doc__ = __doc__.format(toc=compile_toc(toc))
__all__ = [obj.__name__ for section, objs in toc for obj in objs]

__path__ = extend_path(__path__, __name__)
__version__ = '3.0.10'
