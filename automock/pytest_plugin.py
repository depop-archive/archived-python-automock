import pytest

import automock as automock_lib


@pytest.fixture
def automock():
    with automock_lib.activate():
        yield
