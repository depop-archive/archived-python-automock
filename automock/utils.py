from abc import ABCMeta, abstractmethod
from functools import wraps
from typing import Callable, ContextManager, List, Union  # noqa


class ContextDecorator(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def __enter__(self):
        pass

    @abstractmethod
    def __exit__(self, *args):
        pass

    @abstractmethod
    def __call__(self, f):
        pass


class ConditionalContextDecorator(ContextDecorator):
    """
    Wrap another context manager and enter it only if condition is true.

    Adapted from https://github.com/stefanholek/conditional to support
    lazy-callable conditions, and decorators too.
    """

    def __init__(self,
                 condition,  # type: bool
                 context_object,  # type: ContextDecorator
                 ):
        # type: (...) -> None
        """
        Kwargs:
            condition: whether to use the context
            context_object: a context manager or decorator function, or an
                object that can function as both
        """
        self._condition = condition
        self.context_object = context_object

    @property
    def condition(self):
        # type: () -> bool
        """
        NOTE:
        We don't need to use a lazy callable when supplying a django settings
        value as the condition, because the `settings` object already
        implements lazy property access for us.
        """
        if callable(self._condition):
            return self._condition()
        else:
            return self._condition

    def __enter__(self):
        if self.condition:
            return self.context_object.__enter__()

    def __exit__(self, *args):
        if self.condition:
            return self.context_object.__exit__(*args)

    def __call__(self, f):
        # type: (Callable) -> Callable
        """
        Evaluate `condition` on every call to decorated function
        (because this method is being called at import time, so would not
        be possible to eg override_settings to modify the condition value
        if we didn't do it inside `wrapped`)
        """
        @wraps(f)
        def wrapped(*args, **kwargs):
            if self.condition:
                return self.context_object(f)(*args, **kwargs)
            else:
                return f(*args, **kwargs)

        return wrapped


conditional = ConditionalContextDecorator


class MultipleContextDecorator(ContextDecorator):
    """
    A single context-manager/decorator that applies multiple
    context-manager/decorators.

    You can access the individual context returns by index, e.g.

        with multiple(patch(a), patch(b)) as contexts:
            mocked_a = contexts[0]
            mocked_b = contexts[1]

    (same is not possible as decorator though)
    """

    _contexts = None  # type: List[ContextDecorator]

    def __init__(self, *context_decorators):
        # type: (*ContextDecorator) -> None
        self._objects = context_decorators
        self._contexts = []

    def __getitem__(self, key):
        # type: (int) -> ContextDecorator
        return self._contexts[key]

    def __len__(self):
        return len(self._contexts)

    def __enter__(self):
        self._contexts = [
            obj.__enter__()
            for obj in self._objects
        ]
        return self

    def __exit__(self, *args):
        for obj in self._objects:
            obj.__exit__(*args)

    def __call__(self, f):
        # type: (Callable) -> Callable
        decorated = f
        for decorator in self._objects:
            decorated = decorator(decorated)
        return decorated


multiple = MultipleContextDecorator
