import os
from typing import Iterable, Optional  # noqa


# namespace for config keys loaded from e.g. Django conf or env vars
CONFIG_NAMESPACE = os.getenv('AUTOMOCK_CONFIG_NAMESPACE', 'AUTOMOCK')

# optional import path to file containing namespaced config (e.g. 'django.conf.settings')
APP_CONFIG = os.getenv('AUTOMOCK_APP_CONFIG', None)  # type: Optional[str]


# import paths to modules containing `automock.register` calls
REGISTRATION_IMPORTS = ()  # type: Iterable[str]
