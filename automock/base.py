import warnings
from functools import wraps
from importlib import import_module
from typing import Callable, Dict, Optional  # noqa
from unittest import TestCase

from six.moves import mock  # type: ignore

from automock.conf import settings
from automock.utils import MultipleContextDecorator


__all__ = (
    'activate',
    'AutomockTestCaseMixin',
    'AutomockTestCase',
    'start_patching',
    'stop_patching',
    'register',
    'swap_mock',
    'unmock',
    'get_mock',
    'get_called_mocks',
)


_factory_map = {}  # type: Dict[str, Callable]
_patchers = {}  # type: Dict[str, mock.mock._patch]
_mocks = {}  # type: Dict[str, mock.Mock]


def _get_from_path(import_path):
    # type: (str) -> Callable
    """
    Kwargs:
        import_path: full import path (to a mock factory function)

    Returns:
        (the mock factory function)
    """
    module_name, obj_name = import_path.rsplit('.', 1)
    module = import_module(module_name)
    return getattr(module, obj_name)


def register(func_path, factory=mock.MagicMock):
    # type: (str, Callable) -> Callable
    """
    Kwargs:
        func_path: import path to mock (as you would give to `mock.patch`)
        factory: function that returns a mock for the patched func

    Returns:
        (decorator)

    Usage:

        automock.register('path.to.func.to.mock')  # default MagicMock
        automock.register('path.to.func.to.mock', CustomMockFactory)

        @automock.register('path.to.func.to.mock')
        def custom_mock(result):
            return mock.MagicMock(return_value=result)
    """
    global _factory_map
    _factory_map[func_path] = factory

    def decorator(decorated_factory):
        _factory_map[func_path] = decorated_factory
        return decorated_factory

    return decorator


def _pre_import():
    # type: () -> None
    """
    Ensure that modules containing mock factories get imported so that their
    calls to `register` are made.

    (modules which are configured in `TEST_MOCK_FACTORY_MAP` do not need to
    be pre-imported, only those which rely on `register`)
    """
    for import_path in settings.REGISTRATION_IMPORTS:
        import_module(import_path)


def start_patching(name=None):
    # type: (Optional[str]) -> None
    """
    Initiate mocking of the functions listed in `_factory_map`.

    For this to work reliably all mocked helper functions should be imported
    and used like this:

        import dp_paypal.client as paypal
        res = paypal.do_paypal_express_checkout(...)

    (i.e. don't use `from dp_paypal.client import x` import style)

    Kwargs:
        name (Optional[str]): if given, only patch the specified path, else all
            defined default mocks
    """
    global _factory_map, _patchers, _mocks
    if _patchers and name is None:
        warnings.warn('start_patching() called again, already patched')

    _pre_import()

    if name is not None:
        factory = _factory_map[name]
        items = [(name, factory)]
    else:
        items = _factory_map.items()

    for name, factory in items:
        patcher = mock.patch(name, new=factory())
        mocked = patcher.start()
        _patchers[name] = patcher
        _mocks[name] = mocked


def stop_patching(name=None):
    # type: (Optional[str]) -> None
    """
    Finish the mocking initiated by `start_patching`

    Kwargs:
        name (Optional[str]): if given, only unpatch the specified path, else all
            defined default mocks
    """
    global _patchers, _mocks
    if not _patchers:
        warnings.warn('stop_patching() called again, already stopped')

    if name is not None:
        items = [(name, _patchers[name])]
    else:
        items = list(_patchers.items())

    for name, patcher in items:
        patcher.stop()
        del _patchers[name]
        del _mocks[name]


class SwapMockContextDecorator(MultipleContextDecorator):
    """
    Temporarily replace one of our mocked functions with a new mock, using the
    configured mock factory (but generated with different args).

    Use as a decorator or context manager.

    e.g. for a specific test, or part of a test, return a different result

        with swap_mock('services.paypalfees.helpers.user_has_billing_agreement',
                       result_status=PaypalResult.STATUS_FAILURE) as mock_has_billing:
            swapped = get_mock('services.paypalfees.helpers.user_has_billing_agreement')
            assert swapped is mock_has_billing

    ...where `result_status` is a kwarg to the configured mock factory for:
    'services.paypalfees.helpers.user_has_billing_agreement'

    There's nothing to stop you using regular mock.patch instead, this is just a
    helper for making use of configured mock factory functions.
    """

    def __init__(self, _path, *args, **kwargs):
        # type (str, *object, **object) -> None
        """
        Kwargs:
            _path: key in `_factory_map` dict of the method to swap mock for
                (should be an import path)
            *args, **kwargs: passed through to the mock factory used to generate
                a replacement mock to swap in
        """
        global _factory_map
        factory = _factory_map[_path]
        new_mock = factory(*args, **kwargs)
        super(SwapMockContextDecorator, self).__init__(
            mock.patch(_path, new=new_mock),
            mock.patch.dict(_mocks, {_path: new_mock}),
        )

    def __enter__(self):
        # type: () -> Callable
        """
        Returns the context we care about, i.e. the result of the first patch,
        which is the mocked object itself.
        """
        super(SwapMockContextDecorator, self).__enter__()
        return self[0]


swap_mock = SwapMockContextDecorator


class UnMockContextDecorator(object):
    """
    Temporarily un-mock one of our mocked functions, to use the real
    implementation, then replace with the default mock when done.

    Use as a decorator or context manager.

    e.g. for a specific test, or part of a test:

        with unmock('services.paypalfees.helpers.user_has_billing_agreement') as restored:
            assert not isinstance(restored, mock.Mock)
            assert restored.__name__ == 'user_has_billing_agreement'
    """

    def __init__(self, name):
        # type: (str) -> None
        """
        Kwargs:
            _path (str): key in `_factory_map` dict of the method to swap mock for
                (should be an import path)
            *args, **kwargs: passed through to the mock factory used to generate
                a replacement mock to swap in
        """
        self.name = name

    def __enter__(self):
        # type: () -> Callable
        """
        Returns the restored function (calling code may still have a reference
        to the mock even though we stopped patching the source path)
        """
        stop_patching(self.name)
        return _get_from_path(self.name)

    def __exit__(self, *args):
        start_patching(self.name)

    def __call__(self, f):
        # type: (Callable) -> Callable
        """
        Only really useful for test methods, this will inject the restored
        function as an arg (in the same way that @mock.patch decorator does
        with mocked items)
        """
        @wraps(f)
        def decorator(*args):
            stop_patching(self.name)

            restored = _get_from_path(self.name)
            args += (restored,)
            ret = f(*args)

            start_patching(self.name)
            return ret

        return decorator


unmock = UnMockContextDecorator


def get_mock(name):
    # type: (str) -> mock.Mock
    """
    Intended for use in test cases e.g. to check if/how a mock was called

    Emphasises that `_mocks` is a private value. If you need to customise
    mocks use the `swap_mock` helper where possible.
    """
    return _mocks[name]


def get_called_mocks():
    # type: () -> Dict[str, mock.Mock]
    """
    Intended for use in test cases e.g. to check if/how a mock was called

    Emphasises that `_mocks` is a private value. If you need to customise
    mocks use the `swap_mock` helper where possible.
    """
    return {
        name: mock
        for name, mock in _mocks.items()
        if mock.called
    }


class AutomockTestCaseMixin(object):

    def setUp(self):
        start_patching()
        super(AutomockTestCaseMixin, self).setUp()

    def tearDown(self):
        super(AutomockTestCaseMixin, self).tearDown()
        stop_patching()


class AutomockTestCase(AutomockTestCaseMixin, TestCase):
    pass


class ActivateContextDecorator(object):
    """
    If you're not using the `AutomockTestCaseMixin` or the pytest plugin to
    automatically run all your tests with automocks patched, you can manually
    enable automocking with this context-manager/decorator.
    """

    def __enter__(self):
        # type: () -> Callable
        """
        Returns the restored function (calling code may still have a reference
        to the mock even though we stopped patching the source path)
        """
        start_patching()
        return self

    def __exit__(self, *args):
        stop_patching()

    def __call__(self, f):
        # type: (Callable) -> Callable
        @wraps(f)
        def decorator(*args):
            start_patching()
            ret = f(*args)
            stop_patching()
            return ret

        return decorator


activate = ActivateContextDecorator
