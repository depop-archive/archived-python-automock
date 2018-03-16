import automock


def pytest_runtest_setup(item):
    automock.start_patching()


def pytest_runtest_teardown(item):
    automock.stop_patching()
