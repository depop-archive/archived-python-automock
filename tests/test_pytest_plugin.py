
# https://docs.pytest.org/en/latest/writing_plugins.html#testing-plugins
pytest_plugins = 'pytester'


def test_pytest_plugin(testdir):
    testdir.makepyfile("""
import pytest
from six.moves import mock

from tests import dummies


pytest_plugins = 'automock.pytest_plugin'


def test_pytest_plugin():
    # plugin has patched our registered automocks
    assert dummies.func_to_mock() == 'I have large ears'
    assert dummies.other_func_to_mock() == 'I like PHP'
    assert isinstance(dummies.yet_another_func_to_mock(), mock.MagicMock)
    # (no easy way to test but assume if setup worked then teardown also does)
    """)

    result = testdir.runpytest()

    result.assert_outcomes(passed=1)
