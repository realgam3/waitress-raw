#!/usr/bin/env python3

from os import path
from setuptools import setup, find_packages

__folder__ = path.abspath(path.dirname(__file__))

with open(path.join(__folder__, 'README.md')) as readme_file:
    long_description = readme_file.read()

about = {}
with open(path.join(__folder__, 'waitress_raw', '__version__.py')) as about_file:
    exec(about_file.read(), about)

with open(path.join(__folder__, 'requirements.txt')) as req_file:
    install_requires = req_file.readlines()

setup(
    name=about['__title__'],
    version=about['__version__'],
    description=about['__description__'],
    long_description=long_description,
    long_description_content_type='text/markdown',
    author=about['__author__'],
    author_email=about['__author_email__'],
    packages=find_packages(exclude=['examples', 'tests']),
    entry_points={
        "console_scripts": [
            'waitress-raw = waitress_raw:main',
        ]
    },
    python_requires=">=3.7",
    install_requires=install_requires,
    license=about['__license__'],
    platforms='any',
    url=about["__url__"],
    zip_safe=False,
    classifiers=[
        'Environment :: Web Environment',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        "Programming Language :: Python :: 3 :: Only",
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries',
    ],
    project_urls={
        'Source': about["__url__"],
    },
)
