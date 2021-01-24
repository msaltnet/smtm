import io
import unittest
from setuptools import find_packages, setup

# Read in the README for the long description on PyPI
def long_description():
    with io.open('README.md', 'r', encoding='utf-8') as f:
        readme = f.read()
    return readme

def smtm_test_suite():
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='*test.py')
    return test_suite

setup(name='smtm',
    version='0.1',
    description='make money using algorithm with python',
    long_description=long_description(),
    url='https://github.com/msaltnet/smtm',
    author='msalt',
    author_email='salt.jeong@gmail.com',
    license='MIT',
    packages=find_packages(),
    classifiers=[
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.6',
        ],
    install_requires=[
            'requests',
            'matplotlib',
            'pandas',
            'mplfinance'
        ],
    extras_require={
        'dev': [
            'coverage'
        ]
    },
    test_suite='setup.smtm_test_suite',
    zip_safe=False)
