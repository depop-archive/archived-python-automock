from functools import wraps
from unittest import TestCase

from automock.utils import conditional, multiple


class DummyContext(object):

    def __init__(self, value=None):
        self.enabled = False
        self.value = value

    def __enter__(self):
        self.enabled = True
        return self

    def __exit__(self, *args):
        self.enabled = False

    def __call__(self, f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            self.enabled = True
            result = f(*args, **kwargs)
            self.enabled = False
            return result

        return wrapped


class ConditionalContextManagerTestCase(TestCase):

    def test_context_manager_no_conditional(self):
        """
        Basic check that our DummyContext functions as intended as a context manager
        """
        with DummyContext() as context:
            assert isinstance(context, DummyContext)
            assert context.enabled
        assert not context.enabled

    def test_context_manager_true(self):
        """
        Check that conditional manager enters and exits DummyContext
        when condition is True
        """
        with conditional(True, DummyContext()) as context:
            assert isinstance(context, DummyContext)
            assert context.enabled
        assert not context.enabled

    def test_context_manager_false(self):
        """
        Check that conditional manager does not enter DummyContext
        when condition is False
        """
        with conditional(False, DummyContext()) as context:
            assert context is None

    def test_decorator_no_conditional(self):
        """
        Basic check that our DummyContext functions as intended as a decorator
        """
        decorator = DummyContext()

        assert not decorator.enabled

        @decorator
        def test_func(val):
            assert decorator.enabled
            return val + 1

        assert not decorator.enabled

        result = test_func(1)
        assert result == 2
        assert not decorator.enabled

    def test_decorator_basic_true(self):
        """
        Check that conditional manager decorates test_func
        when condition is True
        """
        decorator = conditional(True, DummyContext())

        assert not decorator.context_object.enabled

        @decorator
        def test_func(val):
            assert decorator.context_object.enabled
            return val + 1

        assert not decorator.context_object.enabled

        result = test_func(1)
        assert result == 2
        assert not decorator.context_object.enabled

    def test_decorator_basic_false(self):
        """
        Check that conditional manager decorates test_func
        when condition is False
        """
        decorator = conditional(False, DummyContext())

        assert not decorator.context_object.enabled

        @decorator
        def test_func(val):
            assert not decorator.context_object.enabled
            return val + 1

        assert not decorator.context_object.enabled

        result = test_func(1)
        assert result == 2
        assert not decorator.context_object.enabled

    def test_decorator_callable_true(self):
        """
        Check that conditional manager decorates test_func
        when condition is a callable returning True
        """
        condition = False
        decorator = conditional(lambda: condition, DummyContext())

        assert not decorator.context_object.enabled

        @decorator
        def test_func(val):
            assert decorator.context_object.enabled
            return val + 1

        assert not decorator.context_object.enabled

        condition = True
        result = test_func(1)
        assert result == 2
        assert not decorator.context_object.enabled

    def test_decorator_callable_false(self):
        """
        Check that conditional manager does not decorate test_func
        when condition is a callable returning False
        """
        condition = True
        decorator = conditional(lambda: condition, DummyContext())

        assert not decorator.context_object.enabled

        @decorator
        def test_func(val):
            assert not decorator.context_object.enabled
            return val + 1

        assert not decorator.context_object.enabled

        condition = False
        result = test_func(1)
        assert result == 2
        assert not decorator.context_object.enabled


class MultipleContextManagerTestCase(TestCase):

    def test_context_manager_multiple(self):
        """
        Check that multiple manager enters and exits all supplied managers
        and makes them available via `as` value
        """
        with multiple(DummyContext('wtf'), DummyContext('dude')) as contexts:
            assert len(contexts) == 2

            assert isinstance(contexts[0], DummyContext)
            assert contexts[0].enabled
            assert contexts[0].value == 'wtf'

            assert isinstance(contexts[1], DummyContext)
            assert contexts[1].enabled
            assert contexts[1].value == 'dude'

        assert not contexts[0].enabled
        assert not contexts[1].enabled

    def test_decorator_multiple(self):
        """
        Check that multiple decorator applies all supplied decorators
        """
        decorator = multiple(DummyContext('wtf'), DummyContext('dude'))

        assert not any(manager.enabled for manager in decorator._objects)

        @decorator
        def test_func(val):
            assert all(manager.enabled for manager in decorator._objects)
            return val + 1

        assert not any(manager.enabled for manager in decorator._objects)

        result = test_func(1)
        assert result == 2

        assert not any(manager.enabled for manager in decorator._objects)
