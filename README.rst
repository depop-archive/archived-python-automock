automock
========

|PyPI Version| |Build Status|

.. |PyPI Version| image:: http://img.shields.io/pypi/v/automock.svg?style=flat
   :target: https://pypi.python.org/pypi/automock/
   :alt: Latest PyPI version

.. |Build Status| image:: https://circleci.com/gh/depop/python-automock.svg?style=shield&circle-token=cbe5583fec309912d76bfc8b0321f6cfa23b7f6d
    :alt: Build Status

There are some things that need to be mocked in unit tests.

For example: API clients for other backend services - we don't want to run an
instance of the other service just for our unit tests. The other service will
have its own tests and we only want to test that our code confiorms to the API
contract of the other service. Similarly for 3rd party services - we don't want
our unit tests to connect out over the internet to talk to the 3rd party service
(even if they offer a 'sandbox' test environment) for the same reasons as above,
and because this is a recipe for flaky tests.

(There is certainly a role for integration tests which do make live calls to
other services, but the bulk of tests won't be this kind and need mocking).

Python has the excellent `mock <http://www.voidspace.org.uk/python/mock/>`_ library to help with this.

However, say you have six API clients for backend services which are used
extensively in many places in code for your mobile app backend. You're going to
end up with a big 'stack' of patch decorators on many tests, e.g.:

.. code:: python

    @mock.patch('services.users.client.get_user', return_value=MockUser(id=1))
    @mock.patch('services.products.client.get_product', return_value=MockProduct(id=1))
    @mock.patch('services.paypal.client.make_payment', return_value=PaypalResult('success'))
    def test_some_web_view(self, *mocks)

Say you have thousands of unit tests, these decorators need applying to many of
them. Every time you write a new test you'll need to remember to patch things.

Enter ``automock``.

Basically we want some functions to be 'mocked by default' when running tests.
But we also need to be able to easily replace the default mocks in some cases,
where the test needs a specific return value. ``automock`` makes this easy-ish.


Usage
-----

.. code:: bash

    pip install automock


Introduction
~~~~~~~~~~~~

The key idea is that we define a 'mock factory' for each function we want to be
automocked. When called without arguments the factory should return a suitable
'default' mock that will allow most tests to pass. The default mock factory is
just ``MagicMock`` from the ``mock`` library.

Registering a function to be mocked is simple:

.. code:: python

    import automock

    automock.register('services.users.client.get_user')

By default this provides a ``MagicMock`` and is equivalent to decorating *all*
your test cases with:

.. code:: python

    @mock.patch('services.users.client.get_user')

For this to work you just need to do two things.

#. You need to ensure that the modules containing ``automock.register``
   calls get imported before the tests run. To achieve this we have an
   ``AUTOMOCK_REGISTRATION_IMPORTS`` config setting. This should contain string paths
   to modules containing registration calls, e.g.:

   .. code:: python

        AUTOMOCK_REGISTRATION_IMPORTS = (
            'services.users.test_mocks',
            'services.products.test_mocks',
            'services.paypal.test_mocks',
        )

#. If you're running your tests under `pytest <https://docs.pytest.org/en/latest/>`_
   then you don't need to do anything else - Automock registers a pytest plugin
   (named ``automock`` in pytest) that ensures your test cases all run patched.

#. If you're running under another test-runner then your test cases need to inherit
   from one of our helper classes, e.g.:

   .. code:: python

        from automock import AutomockTestCase, AutomockTestCaseMixin


        class TestWebViews(AutomockTestCase):
            ...


        class TestSpecialViews(AutomockTestCaseMixin, MyCustomTestCase):
            ...

   This will ensure the mock patches get applied before the tests run, and stopped
   afterwards.

   Alternatively you can start/stop patching manually:

   .. code:: python

        from unittest import TestCase

        import automock


        class TestStuff(TestCase):

            # as a decorator
            @automock.activate()
            def test_stuff(self):
                # automocks active
                ...

            # as a context-manager
            def test_other_stuff(self):
                # automocks inactive
                ...
                with automock.activate():
                    # automocks active
                    ...

                # automocks inactive


Configuration
~~~~~~~~~~~~~

Settings are intended to be configured primarily via a python file, such
as your existing Django ``settings.py``. To bootstrap this, there are a couple
of **env vars** to control how config is loaded:

-  ``AUTOMOCK_APP_CONFIG``
   should be an import path to a python module, for example:
   ``AUTOMOCK_APP_CONFIG=django.conf.settings``
-  ``AUTOMOCK_CONFIG_NAMESPACE``
   Sets the prefix used for loading further config values from env and
   config file. Defaults to ``AUTOMOCK``.

The following config keys are available (and are prefixed with
``AUTOMOCK_`` by default, see ``AUTOMOCK_CONFIG_NAMESPACE`` above):

-  ``<namespace>_REGISTRATION_IMPORTS`` list of import paths to modules
   containing ``automock.register`` calls


Patching and imports
~~~~~~~~~~~~~~~~~~~~

An **important point to note** about the path you mock:

This has the same caveats as when using ``mock.patch`` directly. Namely that
you must patch the path *where it is imported*.

For example if you do:

.. code:: python

    # mypackage/mymodule.py

    from services.product.client import get_product

When you patch it:

.. code:: python

    # won't work:
    patch('services.product.client.get_product')

    # works:
    patch('mypackage.mymodule.get_product')

DON'T DO THIS (see this
`blog post <http://bhfsteve.blogspot.co.uk/2012/06/patching-tip-using-mocks-in-python-unit.html>`_
for more details).

This import style will cause us problems if we want to mock-by-default all
usages of a particular function, because we only register a single path to mock.

Instead you need to use one of the following import styles *everywhere* in your
codebase that the function to mocked is used:

.. code:: python

    # mypackage/mymodule.py

    # either
    from services.product import client as product_client
    product_client.get_product(*args)

    # or
    import services.product.client as product_client
    product_client.get_product(*args)

This will ensure that we can:

.. code:: python

    automock.register('services.product.client.get_product')

and have that work reliably.

**NOTE:**

Always ``import automock`` and use as ``automock.register`` to ensure there is
only one registry active.


Customising mock factories
~~~~~~~~~~~~~~~~~~~~~~~~~~

It's likely you need to do more than provide a bare ``MagicMock``. For example
we might want to customise the response based on some values from the request.

In ``mock.Mock`` this is achieved via a 'side effect'. So we might want to
define our mock factory like this:

.. code:: python

    def batch_counters_mock(return_value=None, side_effect=None, *args, **kwargs):
        if return_value is None and side_effect is None:
            def side_effect(product_ids, *args, **kwargs):
                return {str(p_id): 0 for p_id in product_ids}
        return mock.MagicMock(return_value=return_value, side_effect=side_effect, *args, **kwargs)

    automock.register('services.products.client.batch_counters', batch_counters_mock)

Note that we passed the custom mock factory as second argument to ``register``.

As an alternative we can use decorator syntax:

.. code:: python

    @automock.register('services.products.client.batch_counters')
    def batch_counters_mock(return_value=None, side_effect=None, *args, **kwargs):
        if return_value is None and side_effect is None:
            def side_effect(product_ids, *args, **kwargs):
                return {str(p_id): 0 for p_id in product_ids}
        return mock.MagicMock(return_value=return_value, side_effect=side_effect, *args, **kwargs)

Now in our tests we can:

.. code:: python

    import services.products.client as products_client

    def test_counters():
        counters = products_client.batch_counters([1, 2])
        # we got a default value for each of the ids we passed in:
        assert counters == {'1': 0, '2': 0}

(This is a useless test of course, it's just to demonstrate the mocking)

Okay. What if we need a custom return value for a particular test?

Well, firstly the regular ``mock.patch`` still works, you could apply that in
your test case.

Automock also provides a ``swap_mock`` helper that allows us to take advantage
of our custom mock factory.

Let's say our factory looks like:

.. code:: python

    @automock.register('services.things.client.do_something')
    def do_something_mock(success=True):
        if success:
            return mock.MagicMock(return_value='OK')
        else:
            return mock.MagicMock(side_effect=requests.HTTPError())

In our tests we can:

.. code:: python

    import pytest
    import requests
    from automock import swap_mock

    import services.things.client as things_client

    def test_success():
        # default mock from factory gives success response
        assert things_client.do_something() == 'OK'

    @swap_mock('services.things.client.do_something', success=False)
    def test_fail():
        # swap mock applies a customised mock from our factory
        with pytest.raises(requests.HTPPError):
            things_client.do_something()

What happened here is that the ``*args, **kwargs`` from our ``swap_mock`` call
are passed through to the ``do_something_mock`` to *get a new mock* which is
then applied in place of the default.

We can also use this as a context manager:

.. code:: python

    import pytest
    import requests
    from automock import swap_mock

    import services.things.client as things_client

    def test_do_something():
        assert things_client.do_something() == 'OK'

        with swap_mock('services.things.client.do_something', success=False):
            with pytest.raises(requests.HTPPError):
                things_client.do_something()

        assert things_client.do_something() == 'OK'


Checking mocked calls
~~~~~~~~~~~~~~~~~~~~~

It's common in tests to want to check if a mocked function was called, and
with correct arguments etc. If you use ``mock.patch`` directly this is easy
because it returns the mock object to you.

Automock provides the ``get_mock`` helper to achieve the same thing:

.. code:: python

    from automock import get_mock

    import services.things.client as things_client

    def test_success():
        assert things_client.do_something() == 'OK'
        mocked = get_mock('services.things.client.do_something')
        assert mocked.called


Testing the automocked functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ok, so you've mocked your API clients or whatever. How do you test the mocked
functions themselves if they're mocked out everywhere?

Firstly, you could just not inherit from ``AutomockTestCase`` in those tests.

But maybe you have a bunch of other automocks you want to keep in place still.

Automock provides an ``unmock`` helper:

.. code:: python

    import pytest
    import responses
    from automock import unmock

    import services.things.client as things_client

    @responses.activate
    @unmock('services.things.client.do_something')
    def test_do_something_not_found():
        responses.add(responses.GET, 'https://thingservice.ourcompany.com/api/1/something',
                      json={'error': 'Not Found'}, status=404)
        with pytest.raises(requests.HTPPError):
            things_client.do_something()

(for functions which make HTTP calls we recommend the excellent
`responses <https://github.com/getsentry/responses>`_ library)

Here we have un-mocked our client method so that we can test that it correctly
handles a 404 response from the remote service.


Compatibility
-------------

This project is tested against:

=========== ===
Python 2.7   * 
Python 3.6   * 
=========== ===

Running the tests
-----------------

CircleCI
~~~~~~~~

| The easiest way to test the full version matrix is to install the
  CircleCI command line app:
| https://circleci.com/docs/2.0/local-jobs/
| (requires Docker)

The cli does not support 'workflows' at the moment so you have to run
the two Python version jobs separately:

.. code:: bash

    circleci build --job python-2.7

.. code:: bash

    circleci build --job python-3.6

py.test (single python version)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It's also possible to run the tests locally, allowing for debugging of
errors that occur.

Now decide which Python version you want to test and create a virtualenv:

.. code:: bash

    pyenv virtualenv 3.6.4 automock
    pip install -r requirements-test.txt

Now we can run the tests:

.. code:: bash

    make test
