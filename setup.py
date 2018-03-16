from setuptools import setup
from codecs import open  # To use a consistent encoding
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

# Get content from __about__.py
about = {}
with open(path.join(here, 'automock', '__about__.py'), 'r', 'utf-8') as f:
    exec(f.read(), about)


setup(
    name='automock',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=about['__version__'],

    description="Utility to allow some functions to be 'mocked by default' when running tests.",
    long_description=long_description,

    url='https://github.com/depop/python-automock',

    author='Depop',
    author_email='dev@depop.com',

    license='Apache 2.0',
    classifiers=[
        'Environment :: Plugins',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 2.7',
        'Framework :: Pytest',
    ],
    install_requires=[
        'flexisettings>=1.0.1,<1.1',
        'typing>=3.6.2,<4.0',
        'six',
        'mock; python_version < "3"',
    ],

    packages=[
        'automock',
        'automock.conf',
    ],
    entry_points={
        'pytest11': [
            'automock = automock.pytest_plugin',
        ]
    },
)
