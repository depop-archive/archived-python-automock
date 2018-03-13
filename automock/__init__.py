from six import add_move, MovedModule  # type: ignore
add_move(MovedModule('mock', 'mock', 'unittest.mock'))

from automock.base import *  # noqa
