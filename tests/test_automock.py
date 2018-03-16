from unittest import TestCase

from six.moves import mock

from automock import (
    activate,
    AutomockTestCase,
    get_mock,
    start_patching,
    stop_patching,
    swap_mock,
    unmock,
)
from automock.base import _factory_map, _pre_import

from tests import dummies


MOCK_PATH = 'tests.dummies.func_to_mock'
OTHER_MOCK_PATH = 'tests.dummies.other_func_to_mock'
YET_ANOTHER_MOCK_PATH = 'tests.dummies.yet_another_func_to_mock'


class Registration(TestCase):

    def setUp(self):
        _pre_import()

    def test_decorator(self):
        assert MOCK_PATH in _factory_map
        assert _factory_map[MOCK_PATH]().return_value == 'I have large ears'

    def test_register_custom_factory(self):
        assert OTHER_MOCK_PATH in _factory_map
        assert _factory_map[OTHER_MOCK_PATH]().return_value == 'I like PHP'

    def test_register_default_factory(self):
        assert YET_ANOTHER_MOCK_PATH in _factory_map
        assert _factory_map[YET_ANOTHER_MOCK_PATH] is mock.MagicMock


class StartStopPatching(TestCase):

    def test_start_stop(self):
        # unmocked
        assert dummies.func_to_mock() == 'Go ahead, mock me'
        assert dummies.other_func_to_mock() == 'Go ahead, mock me 2'
        assert dummies.yet_another_func_to_mock() == 'Go ahead, mock me 3'

        start_patching()

        # mocked
        assert dummies.func_to_mock() == 'I have large ears'
        assert dummies.other_func_to_mock() == 'I like PHP'
        assert isinstance(dummies.yet_another_func_to_mock(), mock.MagicMock)

        stop_patching()

        # unmocked
        assert dummies.func_to_mock() == 'Go ahead, mock me'
        assert dummies.other_func_to_mock() == 'Go ahead, mock me 2'
        assert dummies.yet_another_func_to_mock() == 'Go ahead, mock me 3'

    def test_get_mock(self):
        start_patching()
        mocked = get_mock(MOCK_PATH)
        assert mocked.return_value == 'I have large ears'
        stop_patching()


class SwapMockContextDecoratorTestCase(TestCase):

    def test_context_manager(self):
        start_patching()
        try:
            with swap_mock(MOCK_PATH, mockery='I smell funny') as mocked:
                # we have swapped mock for target func
                assert dummies.func_to_mock() == 'I smell funny'

                # `as` returns the swapped mock
                assert mocked.return_value == 'I smell funny'

                # _mocks dict was patched too
                swapped = get_mock(MOCK_PATH)
                assert swapped is mocked

            # default mock was restored
            assert dummies.func_to_mock() == 'I have large ears'

            # _mocks dict was restored
            swapped = get_mock(MOCK_PATH)
            assert swapped.return_value == 'I have large ears'
        finally:
            stop_patching()

    def test_decorator(self):
        start_patching()
        try:
            decorator = swap_mock(MOCK_PATH, mockery='I smell funny')

            assert dummies.func_to_mock() == 'I have large ears'

            @decorator
            def test_func(val):
                # we have swapped mock for target func
                assert dummies.func_to_mock() == 'I smell funny'

                # _mocks dict was patched too
                swapped = get_mock(MOCK_PATH)
                assert swapped.return_value == 'I smell funny'

                return val + 1

            assert dummies.func_to_mock() == 'I have large ears'

            result = test_func(1)
            assert result == 2

            # default mock was restored after calling func
            assert dummies.func_to_mock() == 'I have large ears'

            # _mocks dict was restored
            swapped = get_mock(MOCK_PATH)
            assert swapped.return_value == 'I have large ears'
        finally:
            stop_patching()


class UnMockContextDecoratorTestCase(TestCase):

    def test_context_manager(self):
        start_patching()
        try:
            with unmock(MOCK_PATH) as restored:
                # mock was cleared
                with self.assertRaises(KeyError):
                    get_mock(MOCK_PATH)

                # other mocks un-touched
                get_mock(OTHER_MOCK_PATH)

                # we have restored real implementation of target func
                assert restored() == 'Go ahead, mock me'

            # default mock was re-enabled
            assert dummies.func_to_mock() == 'I have large ears'

            # _mocks dict was restored
            swapped = get_mock(MOCK_PATH)
            assert swapped.return_value == 'I have large ears'
        finally:
            stop_patching()

    def test_decorator(self):
        start_patching()
        try:
            decorator = unmock(MOCK_PATH)

            assert dummies.func_to_mock() == 'I have large ears'

            @decorator
            def test_func(val, restored):
                # we have restored real implementation of target func
                assert restored() == 'Go ahead, mock me'

                # mock was cleared
                with self.assertRaises(KeyError):
                    get_mock(MOCK_PATH)

                # other mocks un-touched
                get_mock(OTHER_MOCK_PATH)

                return val + 1

            assert dummies.func_to_mock() == 'I have large ears'

            result = test_func(1)
            assert result == 2

            # default mock still in place after calling func
            assert dummies.func_to_mock() == 'I have large ears'

            # _mocks dict was restored
            swapped = get_mock(MOCK_PATH)
            assert swapped.return_value == 'I have large ears'
        finally:
            stop_patching()


class TestAutomockTestCase(AutomockTestCase):

    def test_patched(self):
        # mocked
        assert dummies.func_to_mock() == 'I have large ears'
        assert dummies.other_func_to_mock() == 'I like PHP'
        assert isinstance(dummies.yet_another_func_to_mock(), mock.MagicMock)


def test_activate_context_manager():
    # unmocked
    assert dummies.func_to_mock() == 'Go ahead, mock me'
    assert dummies.other_func_to_mock() == 'Go ahead, mock me 2'
    assert dummies.yet_another_func_to_mock() == 'Go ahead, mock me 3'

    with activate():
        # mocked
        assert dummies.func_to_mock() == 'I have large ears'
        assert dummies.other_func_to_mock() == 'I like PHP'
        assert isinstance(dummies.yet_another_func_to_mock(), mock.MagicMock)

    # unmocked
    assert dummies.func_to_mock() == 'Go ahead, mock me'
    assert dummies.other_func_to_mock() == 'Go ahead, mock me 2'
    assert dummies.yet_another_func_to_mock() == 'Go ahead, mock me 3'


def test_activate_decorator():
    # unmocked
    assert dummies.func_to_mock() == 'Go ahead, mock me'
    assert dummies.other_func_to_mock() == 'Go ahead, mock me 2'
    assert dummies.yet_another_func_to_mock() == 'Go ahead, mock me 3'

    @activate()
    def test_func(fix1):
        assert fix1 == 'OK'
        # mocked
        assert dummies.func_to_mock() == 'I have large ears'
        assert dummies.other_func_to_mock() == 'I like PHP'
        assert isinstance(dummies.yet_another_func_to_mock(), mock.MagicMock)

    test_func('OK')

    # unmocked
    assert dummies.func_to_mock() == 'Go ahead, mock me'
    assert dummies.other_func_to_mock() == 'Go ahead, mock me 2'
    assert dummies.yet_another_func_to_mock() == 'Go ahead, mock me 3'
