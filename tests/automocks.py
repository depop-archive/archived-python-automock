from functools import partial

import automock
from six.moves import mock


@automock.register('tests.test_automock.func_to_mock')
def mock_factory(mockery='I have large ears'):
    mocked = mock.MagicMock()
    mocked.return_value = mockery
    return mocked


custom_mock_factory = partial(mock_factory, 'I like PHP')

automock.register('tests.test_automock.other_func_to_mock', custom_mock_factory)
automock.register('tests.test_automock.yet_another_func_to_mock')
