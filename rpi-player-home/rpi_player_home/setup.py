from __future__ import unicode_literals

import re

from setuptools import find_packages, setup


def get_version(filename):
    with open(filename) as fh:
        metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", fh.read()))
        return metadata['version']


setup(
    name='Mopidy-RPI-Player-Home',
    version=get_version('mopidy_rpi_player_home/__init__.py'),
    url='https://github.com/drudv/rpi-player',
    license='MIT',
    author='Dmitry Druganov',
    author_email='drud@drud.cz',
    description='Mopidy extension for RPI Player welcome page',
    # long_description=open('README.md').read(),
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'setuptools',
        'Mopidy >= 1.0',
        'Pykka >= 1.1',
        'Jinja2 >= 2.7',
    ],
    entry_points={
        'mopidy.ext': [
            'rpi_player_home = mopidy_rpi_player_home:Extension',
        ],
    },
    classifiers=[
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Multimedia :: Sound/Audio :: Players',
    ],
)
