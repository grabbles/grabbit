import sys
from setuptools import setup, find_packages

if len(set(('test', 'easy_install')).intersection(sys.argv)) > 0:
    import setuptools

tests_require = []

VERSION = "0.1.1"

setup(
    name="grabbit",
    version=VERSION,
    description="get grabby with file trees",
    maintainer='Tal Yarkoni',
    maintainer_email='tyarkoni@gmail.com',
    url='http://github.com/grabbles/grabbit',
    packages=find_packages(exclude=['tests', 'test_*']),
    package_data={'grabbit.tests': ['data/*']},
    install_requires=[],
    tests_require=tests_require,
    license='MIT',
    download_url='http://github.com/grabbles/grabbit/archive/%s.tar.gz' % VERSION,
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ]
)
